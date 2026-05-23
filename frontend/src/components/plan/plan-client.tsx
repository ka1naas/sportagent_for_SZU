"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Container } from "@/components/ui/container";
import { Input } from "@/components/ui/input";
import { sendAssistantMessage } from "@/lib/api/assistant";
import { usePlannerStore } from "@/stores/planner-store";

function formatDietValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }

  if (Array.isArray(value)) {
    return value.length > 0 ? value.map((item) => formatDietValue(item)).join("、") : "—";
  }

  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, nestedValue]) => `${key}：${formatDietValue(nestedValue)}`)
      .join("；");
  }

  return String(value);
}

function extractErrorMessage(error: unknown) {
  if (!(error instanceof Error)) {
    return "请求失败，请稍后重试。";
  }

  try {
    const parsed = JSON.parse(error.message) as { detail?: string };
    return parsed.detail ?? error.message;
  } catch {
    if (error.message === "Failed to fetch") {
      return "无法连接到后端服务。请确认后端已启动，并且可通过 http://127.0.0.1:8000 正常访问。";
    }

    return error.message;
  }
}

function formatDisplayId(value: string | null, prefix: string) {
  if (!value) {
    return "未生成";
  }

  const compact = value.replace(/^guest_/, "").replace(/-/g, "").slice(0, 6).toUpperCase();
  return `${prefix}-${compact || "000000"}`;
}

const DIET_FIELD_LABELS: Record<string, string> = {
  canteen: "食堂",
  stall: "档口",
  price: "价格",
  protein_g: "蛋白质(g)",
  carb_g: "碳水(g)",
  fat_g: "脂肪(g)",
  calories: "热量",
  timing: "建议时间",
  note: "备注",
  meal_type: "餐次",
  reason: "推荐理由",
  category: "类别",
  name: "名称",
};

function formatDietCellValue(key: string, value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (key === "price") {
    return `¥${value}`;
  }

  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join("、");
  }

  return String(value);
}

function getDietTableRows(dietPlan: Record<string, unknown> | null | undefined) {
  if (!dietPlan || typeof dietPlan !== "object") {
    return [] as Array<Record<string, string>>;
  }

  const candidateEntries = Object.values(dietPlan).filter((value) => Array.isArray(value)) as unknown[][];
  const candidateList = candidateEntries.find((items) =>
    items.some((item) => typeof item === "object" && item !== null && ("canteen" in (item as Record<string, unknown>) || "stall" in (item as Record<string, unknown>))),
  );

  if (!candidateList) {
    return [];
  }

  return candidateList
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => {
      const row: Record<string, string> = {};
      Object.entries(item).forEach(([key, value]) => {
        const mappedKey = DIET_FIELD_LABELS[key];
        if (!mappedKey) {
          return;
        }

        row[mappedKey] = formatDietCellValue(key, value);
      });

      return row;
    })
    .filter((row) => Object.keys(row).length > 0);
}

function getDietPlanSections(dietPlan: Record<string, unknown> | null | undefined) {
  if (!dietPlan || typeof dietPlan !== "object") {
    return [] as Array<{ title: string; lines: string[] }>;
  }

  const hiddenKeys = new Set([
    "message",
    "raw",
    "meta",
    "debug",
    "prompt_context",
    "recommend",
    "recommendation",
    "recommendations",
    "recommand",
    "daily_target",
    "daily_targets",
    "macro_target",
    "macro_targets",
    "calorie_target",
    "calorie_targets",
    "protein_target",
    "carb_target",
    "fat_target",
  ]);

  return Object.entries(dietPlan)
    .filter(([key, value]) => !hiddenKeys.has(key) && value !== null && value !== undefined && formatDietValue(value) !== "—")
    .map(([key, value]) => ({
      title: key,
      lines: Array.isArray(value)
        ? value.map((item) => formatDietValue(item)).filter((line) => line && /[\u4e00-\u9fa5]/.test(line))
        : typeof value === "object"
          ? Object.entries(value as Record<string, unknown>)
              .filter(([nestedKey]) => /[\u4e00-\u9fa5]/.test(nestedKey))
              .map(([nestedKey, nestedValue]) => `${nestedKey}：${formatDietValue(nestedValue)}`)
          : /[\u4e00-\u9fa5]/.test(formatDietValue(value))
            ? [formatDietValue(value)]
            : [],
    }))
    .filter((section) => section.lines.length > 0);
}

export function PlanClient() {
  const {
    structuredPlan,
    planText,
    planId,
    sessionId,
    changeSummary,
    latestAssistantMessage,
    latestRouteKind,
    latestWeatherStatus,
    answers,
    setPlanResult,
    setRefineResult,
    setLatestWeatherStatus,
    setLatestRouteKind,
    setLatestAssistantMessage,
  } = usePlannerStore();

  const [input, setInput] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const schedule = structuredPlan?.weekly_schedule ?? [];
  const warnings = structuredPlan?.warnings ?? [];

  const weatherSummary = useMemo(() => {
    if (!latestWeatherStatus) {
      return null;
    }

    const bestVenue = [...latestWeatherStatus.venue_statuses].sort((a, b) => b.suitability_score - a.suitability_score)[0];
    if (!bestVenue) {
      return "当前没有可用的场馆状态数据。";
    }

    return `当前${latestWeatherStatus.weather_snapshot.is_raining ? "在下雨" : "天气稳定"}，优先推荐 ${bestVenue.venue_name}。${bestVenue.notice}`;
  }, [latestWeatherStatus]);

  const collectedFacts = useMemo(
    () => [
      ["身体基础", answers.profile ? `${answers.profile.gender} / ${answers.profile.height_cm}cm / ${answers.profile.weight_kg}kg` : "未填写"],
      ["训练目标", answers.goal?.goal ?? "未填写"],
      ["训练频率", answers.spaceTime?.frequency ?? "未填写"],
      ["饮食预算", answers.diet?.weekly_budget ?? "未填写"],
      ["运动习惯", answers.habits?.favorite_sport ?? "未填写"],
    ],
    [answers],
  );

  const dietRows = useMemo(() => {
    if (!structuredPlan?.diet_plan || typeof structuredPlan.diet_plan !== "object") {
      return [];
    }

    return Object.entries(structuredPlan.diet_plan).map(([key, value]) => ({
      label: key,
      value: formatDietValue(value),
    }));
  }, [structuredPlan]);

  const dietSections = useMemo(() => getDietPlanSections(structuredPlan?.diet_plan), [structuredPlan]);
  const dietTableRows = useMemo(() => getDietTableRows(structuredPlan?.diet_plan), [structuredPlan]);

  async function handleSubmit() {
    const message = input.trim();
    if (!message || isSubmitting) {
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      if (!sessionId) {
        throw new Error("当前会话不存在，请先完成五步规划。");
      }

      const response = await sendAssistantMessage({
        session_id: sessionId,
        plan_id: planId,
        message,
      });

      setLatestRouteKind(response.route_kind);

      if (response.route_kind === "generate_plan") {
        if (!response.plan_id || !response.structured_plan) {
          throw new Error("生成计划成功，但返回数据不完整。");
        }

        setPlanResult({
          planId: response.plan_id,
          planText: response.assistant_message,
          structuredPlan: response.structured_plan,
        });
        setInput("");
        return;
      }

      if (response.route_kind === "refine_plan") {
        if (!response.structured_plan) {
          throw new Error("修改计划成功，但返回数据不完整。");
        }

        setRefineResult({
          structuredPlan: response.structured_plan,
          changeSummary: response.change_summary ?? "已根据你的反馈更新计划。",
          assistantMessage: response.assistant_message,
        });
        setInput("");
        return;
      }

      if (response.route_kind === "weather_check") {
        setLatestAssistantMessage(response.assistant_message, "weather_check");

        if (response.weather_snapshot) {
          setLatestWeatherStatus(
            {
              location: "深圳大学",
              weather_snapshot: response.weather_snapshot,
              venue_statuses: response.venue_statuses,
            },
            response.assistant_message,
          );
        }
        setInput("");
        return;
      }

      setInput("");
    } catch (error) {
      setErrorMessage(extractErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="pb-16 pt-8 md:pt-10">
      <Container>
        <div className="space-y-6">
          <Card className="border-border/80 bg-white/90">
            <CardContent className="flex flex-col gap-6 p-6 md:flex-row md:items-end md:justify-between md:p-8">
              <div className="space-y-4">
                <Badge tone="success">Plan + Refine + Visualize</Badge>
                <div>
                  <h1 className="text-3xl font-bold text-foreground md:text-5xl">本周训练计划</h1>
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-muted md:text-base">查看本周安排，或直接在上方智能对话里继续提要求。</p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  ["会话编号", formatDisplayId(sessionId || null, "SESSION")],
                  ["计划编号", formatDisplayId(planId, "PLAN")],
                  ["训练单元", `${schedule.length}`],
                  ["天气提醒", `${warnings.length}`],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-3xl border border-border bg-background px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
                    <p className="mt-2 break-all text-sm font-semibold text-foreground">{value}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="bg-white/90">
              <CardContent className="space-y-4 p-5 md:p-6 lg:p-7">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold text-foreground">智能对话</h2>
                    <p className="mt-2 text-sm leading-6 text-muted">可使用功能：天气查询、计划修改。直接输入你的问题，系统会自动识别调用对应能力。</p>
                  </div>
                  {latestRouteKind ? <Badge tone="muted">当前能力：{latestRouteKind}</Badge> : null}
                </div>

                <div className="grid gap-3 lg:grid-cols-[1fr_auto]">
                  <Input placeholder="例如：现在天气怎么样？或者把周三晚上的训练移到周五下午。" value={input} onChange={(event) => setInput(event.target.value)} />
                  <Button onClick={handleSubmit} disabled={isSubmitting} className="lg:min-w-[132px]">
                    {isSubmitting ? "处理中..." : "发送"}
                  </Button>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-[24px] bg-background p-5 text-sm leading-7 text-muted">
                    <p className="font-medium text-foreground">最近一次 AI 回复</p>
                    <p className="mt-3 whitespace-pre-wrap">{latestAssistantMessage ?? "你提交问题后，这里会展示 AI 的最新说明。"}</p>
                  </div>

                  <div className="rounded-[24px] border border-dashed border-primary/20 bg-[#f7fbf9] p-5 text-sm leading-7 text-muted">
                    <p className="font-medium text-foreground">最近修改摘要</p>
                    <p className="mt-3 whitespace-pre-wrap">{changeSummary ?? "当你提出计划修改要求时，这里会展示本轮改动摘要。"}</p>
                  </div>
                </div>

                {latestRouteKind === "weather_check" ? (
                  <div className="rounded-[24px] border border-dashed border-primary/25 bg-[#eef8f4] p-5 text-sm leading-7 text-muted">
                    <p className="font-medium text-foreground">天气查询结果</p>
                    <p className="mt-3 whitespace-pre-wrap">{latestAssistantMessage ?? "天气查询已完成，但当前没有返回可展示的文本结果。"}</p>
                    {weatherSummary ? <p className="mt-3 text-foreground">{weatherSummary}</p> : null}
                  </div>
                ) : null}

                {errorMessage ? <p className="text-sm text-[#b42318]">{errorMessage}</p> : null}
              </CardContent>
            </Card>

            <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
              <div className="space-y-6">
                <Card className="bg-white/90">
                  <CardContent className="space-y-5 p-5 md:p-6">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h2 className="text-xl font-semibold text-foreground">计划总览</h2>
                        <p className="mt-2 text-sm leading-6 text-muted">通过结构化时间轴展示每周训练安排，计划被修改后这里会立刻重绘。</p>
                      </div>
                      {latestRouteKind ? <Badge tone="muted">最近路由：{latestRouteKind}</Badge> : null}
                    </div>

                    {structuredPlan ? (
                      <>
                        <div className="rounded-[28px] bg-background p-5">
                          <p className="text-sm font-semibold text-foreground">AI 计划摘要</p>
                          <p className="mt-3 text-sm leading-7 text-muted">{structuredPlan.plan_summary}</p>
                        </div>

                        <div className="rounded-[28px] border border-dashed border-primary/20 bg-[#f7fbf9] p-5 text-sm leading-7 text-muted">
                          <span className="font-medium text-foreground">计划可视化说明：</span> 下方训练表单独展示每个训练日的结构化安排，修改计划后也会在该栏目直接刷新。
                        </div>
                      </>
                    ) : (
                      <div className="rounded-[30px] bg-background p-8 text-center">
                        <h2 className="text-2xl font-semibold text-foreground">还没有生成训练计划</h2>
                        <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-muted">
                          先去前面的五信息点采集页完成输入，AI 才能读取场馆信息并生成可修改的结构化计划。
                        </p>
                        <div className="mt-5">
                          <Button asChild>
                            <a href="/planner">去完成五步采集</a>
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card className="bg-white/90">
                  <CardContent className="space-y-5 p-5 md:p-6">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h2 className="text-xl font-semibold text-foreground">本周计划表</h2>
                        <p className="mt-2 text-sm leading-6 text-muted">训练计划表单独占一个栏目，专门用于展示按天拆分的结构化训练安排。</p>
                      </div>
                      <Badge tone="muted">训练表</Badge>
                    </div>

                    {structuredPlan ? (
                      <>
                        <div className="space-y-4">
                          {schedule.map((item, index) => (
                            <div key={item.item_id} className="grid gap-4 rounded-[30px] border border-border bg-white p-5 shadow-sm lg:grid-cols-[90px_1fr]">
                              <div className="flex flex-col items-start justify-between rounded-[24px] bg-background px-4 py-4">
                                <span className="text-xs uppercase tracking-[0.24em] text-muted">Day {index + 1}</span>
                                <div>
                                  <p className="text-lg font-semibold text-foreground">{item.day}</p>
                                  <p className="mt-1 text-sm text-muted">{item.time_period}</p>
                                </div>
                              </div>

                              <div className="space-y-4">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                  <div>
                                    <h3 className="text-lg font-semibold text-foreground">{item.title}</h3>
                                    <p className="mt-1 text-sm text-muted">
                                      {item.location} · {item.location_type} · {item.training_type}
                                    </p>
                                  </div>
                                  <Badge>{item.training_type}</Badge>
                                </div>

                                <div className="grid gap-3 md:grid-cols-2">
                                  {item.items.map((detail) => (
                                    <div key={detail} className="rounded-2xl bg-background px-4 py-3 text-sm leading-6 text-muted">
                                      {detail}
                                    </div>
                                  ))}
                                </div>

                                {item.fallback ? (
                                  <div className="rounded-2xl border border-dashed border-primary/20 bg-[#f7fbf9] p-4 text-sm leading-6 text-muted">
                                    <span className="font-medium text-foreground">天气备选：</span>
                                    {item.fallback}
                                  </div>
                                ) : null}

                                {item.notes ? <p className="text-sm leading-6 text-muted">{item.notes}</p> : null}
                              </div>
                            </div>
                          ))}
                        </div>

                        {changeSummary ? (
                          <div className="rounded-[28px] border border-dashed border-primary/20 bg-[#f7fbf9] p-5 text-sm leading-7 text-muted">
                            <span className="font-medium text-foreground">本轮计划修改说明：</span> {changeSummary}
                          </div>
                        ) : null}
                      </>
                    ) : (
                      <div className="rounded-[28px] bg-background p-6 text-sm leading-7 text-muted">
                        计划生成完成后，这里会以独立栏目展示完整计划表。
                      </div>
                    )}
                  </CardContent>
                </Card>

              </div>

              <div className="space-y-6">
                <Card className="bg-white/90">
                  <CardContent className="space-y-4 p-5">
                    <h2 className="text-lg font-semibold text-foreground">五个信息点快照</h2>
                    <div className="space-y-3">
                      {collectedFacts.map(([label, value]) => (
                        <div key={label} className="rounded-2xl bg-background px-4 py-4">
                          <p className="text-xs uppercase tracking-[0.2em] text-muted">{label}</p>
                          <p className="mt-2 text-sm font-medium leading-6 text-foreground">{value}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-white/90">
                  <CardContent className="space-y-4 p-5">
                    <h2 className="text-lg font-semibold text-foreground">天气 / 场馆判断</h2>
                    {weatherSummary ? (
                      <p className="text-sm leading-6 text-muted">{weatherSummary}</p>
                    ) : (
                      <p className="text-sm leading-6 text-muted">当用户询问“现在能不能练”时，这里会显示天气与场馆联动结果。</p>
                    )}
                    {warnings.length > 0 ? (
                      <ul className="space-y-3 text-sm leading-6 text-muted">
                        {warnings.map((warning) => (
                          <li key={warning}>• {warning}</li>
                        ))}
                      </ul>
                    ) : (
                      <div className="rounded-2xl bg-background p-4 text-sm leading-6 text-muted">当前没有额外风险提示。</div>
                    )}
                  </CardContent>
                </Card>

                <Card className="bg-white/90">
                  <CardContent className="space-y-4 p-5">
                    <div>
                      <h2 className="text-lg font-semibold text-foreground">饮食计划表</h2>
                      <p className="mt-2 text-sm leading-6 text-muted">饮食数据改为表格化展示，便于和训练计划一起查看。</p>
                    </div>

                    {dietTableRows.length > 0 ? (
                      <div className="overflow-hidden rounded-[24px] border border-border bg-background">
                        <div className="grid grid-cols-6 gap-0 border-b border-border bg-secondary/40 text-sm font-semibold text-foreground">
                          {["食堂", "档口", "价格", "蛋白质(g)", "建议时间", "备注"].map((header) => (
                            <div key={header} className="px-4 py-3">
                              {header}
                            </div>
                          ))}
                        </div>
                        {dietTableRows.map((row, index) => (
                          <div key={`${row["食堂"]}-${row["档口"]}-${index}`} className="grid grid-cols-6 gap-0 border-b border-border/70 text-sm leading-6 text-muted last:border-b-0">
                            <div className="px-4 py-3 text-foreground">{row["食堂"] ?? "—"}</div>
                            <div className="px-4 py-3 text-foreground">{row["档口"] ?? "—"}</div>
                            <div className="px-4 py-3">{row["价格"] ?? "—"}</div>
                            <div className="px-4 py-3">{row["蛋白质(g)"] ?? "—"}</div>
                            <div className="px-4 py-3">{row["建议时间"] ?? "—"}</div>
                            <div className="px-4 py-3">{row["备注"] ?? "—"}</div>
                          </div>
                        ))}
                      </div>
                    ) : dietSections.length > 0 ? (
                      <div className="space-y-4">
                        {dietSections.map((section, index) => (
                          <div key={section.title} className="grid gap-4 rounded-[30px] border border-border bg-white p-5 shadow-sm lg:grid-cols-[90px_1fr]">
                            <div className="flex flex-col items-start justify-between rounded-[24px] bg-background px-4 py-4">
                              <span className="text-xs uppercase tracking-[0.24em] text-muted">Diet {index + 1}</span>
                              <div>
                                <p className="text-lg font-semibold text-foreground">{section.title}</p>
                                <p className="mt-1 text-sm text-muted">饮食建议</p>
                              </div>
                            </div>

                            <div className="space-y-4">
                              <div className="grid gap-3 md:grid-cols-2">
                                {section.lines.map((line) => (
                                  <div key={line} className="rounded-2xl bg-background px-4 py-3 text-sm leading-6 text-muted">
                                    {line}
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : dietRows.length > 0 ? (
                      <div className="space-y-4">
                        {dietRows.map((row, index) => (
                          <div key={row.label} className="grid gap-4 rounded-[30px] border border-border bg-white p-5 shadow-sm lg:grid-cols-[90px_1fr]">
                            <div className="flex flex-col items-start justify-between rounded-[24px] bg-background px-4 py-4">
                              <span className="text-xs uppercase tracking-[0.24em] text-muted">Diet {index + 1}</span>
                              <div>
                                <p className="text-lg font-semibold text-foreground">{row.label}</p>
                                <p className="mt-1 text-sm text-muted">饮食建议</p>
                              </div>
                            </div>

                            <div className="rounded-2xl bg-background px-4 py-4 text-sm leading-6 text-muted">{row.value}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-[24px] bg-background p-4 text-sm leading-6 text-muted">尚未生成饮食计划数据。</div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </Container>
    </main>
  );
}
