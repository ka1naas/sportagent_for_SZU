"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Container } from "@/components/ui/container";
import { Input } from "@/components/ui/input";
import { ProgressSteps } from "@/components/ui/progress-steps";
import { Textarea } from "@/components/ui/textarea";
import { sendAssistantMessage } from "@/lib/api/assistant";
import {
  submitDietStep,
  submitGoalStep,
  submitHabitStep,
  submitProfileStep,
  submitSpaceTimeStep,
} from "@/lib/api/chat";
import {
  persistDemoScheduleFlag,
  persistSessionId,
  readDemoScheduleFlag,
  readStoredSessionId,
} from "@/lib/session";
import { createGuestSessionId, usePlannerStore } from "@/stores/planner-store";
import type { StepName } from "@/types/chat";

const stepOrder: StepName[] = ["step1_profile", "step2_goal", "step3_space_time", "step4_diet", "step5_habits"];

const stepMeta: Record<
  StepName,
  {
    title: string;
    shortTitle: string;
    prompt: string;
    hint: string;
    metric: string;
  }
> = {
  step1_profile: {
    title: "采集 1/5 · 身体基础",
    shortTitle: "身体基础",
    prompt: "先确认你的身体基础，这会直接影响训练负荷和恢复节奏。",
    hint: "录入性别、身高、体重，后端会按真实字段保存。",
    metric: "体型基线",
  },
  step2_goal: {
    title: "采集 2/5 · 训练目标",
    shortTitle: "训练目标",
    prompt: "明确主要目标后，AI 才能判断要优先安排减脂、增肌还是耐力推进。",
    hint: "这里决定计划的主方向与训练结构。",
    metric: "目标约束",
  },
  step3_space_time: {
    title: "采集 3/5 · 时间与场地",
    shortTitle: "时间场地",
    prompt: "结合宿舍区、训练频率和时间偏好，让 AI 能自动匹配体育场馆与训练时段。",
    hint: "课表信息按你的要求先写死为一份固定课表，只给 AI 分析，不做替代上传。",
    metric: "时空约束",
  },
  step4_diet: {
    title: "采集 4/5 · 饮食预算",
    shortTitle: "饮食预算",
    prompt: "饮食预算与食堂偏好会影响计划中的补给建议和训练日安排。",
    hint: "继续使用真实 API 字段，不增加伪数据路径。",
    metric: "预算条件",
  },
  step5_habits: {
    title: "采集 5/5 · 运动习惯",
    shortTitle: "运动习惯",
    prompt: "最后一问用于让计划更像你的日常习惯，而不是一份泛化模板。",
    hint: "提交后立即触发 AI 生成初版计划。",
    metric: "偏好修正",
  },
  completed: {
    title: "五项信息已采集完成",
    shortTitle: "采集完成",
    prompt: "全部信息已准备完毕，可以直接进入计划生成。",
    hint: "如果已成功生成计划，会自动跳转到计划页。",
    metric: "就绪状态",
  },
};

const genderOptions = ["男", "女", "第三性别"] as const;
const goalOptions = ["减脂", "增肌", "力量", "爆发力", "耐力"] as const;
const muscleLossOptions = ["接受", "不接受"] as const;
const frequencyOptions = ["1-2次", "3-4次", "5次以上"] as const;
const durationOptions = ["30分钟内", "45-60分钟", "1小时以上"] as const;
const preferenceOptions = ["上课前", "下课后", "无所谓"] as const;
const budgetOptions = ["极限穷鬼<300元", "普通学生300-500元", "宽裕>500元"] as const;
const sportOptions = ["篮球", "骑行", "跑步", "羽毛球", "健身", "不爱运动", "其他"] as const;
const commonCanteenOptions = ["听荔餐厅", "南区食堂", "西南食堂", "荔园食堂", "清真窗口"];
const fixedScheduleSummary = [
  "周一 08:00-11:30 专业课，19:00 后空闲",
  "周二 10:00-12:00 实验课，16:00 后空闲",
  "周三 08:00-17:00 满课，仅 21:00 后可安排轻训练",
  "周四 下午课程较少，15:00 后适合中等强度训练",
  "周五 14:00 后基本空闲，适合安排完整训练单元",
];

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

function extractStepFromMessage(message: string): StepName | null {
  const matchedStep = stepOrder.find((step) => message.includes(step));
  return matchedStep ?? null;
}

function StepOptionButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={active ? "rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-soft" : "rounded-full border border-border bg-white px-4 py-2 text-sm text-foreground transition hover:border-primary/40 hover:bg-secondary"}
    >
      {label}
    </button>
  );
}

export function PlannerClient() {
  const router = useRouter();
  const {
    sessionId,
    currentStep,
    hasDemoSchedule,
    answers,
    setSessionId,
    setCurrentStep,
    setHasDemoSchedule,
    resetPlanOutputs,
    updateAnswers,
    setPlanResult,
  } = usePlannerStore();

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [canteenDraft, setCanteenDraft] = useState("");
  const [contextNote, setContextNote] = useState("");
  const [generationProgress, setGenerationProgress] = useState(0);
  const [showGenerationOverlay, setShowGenerationOverlay] = useState(false);
  const [generationStatusText, setGenerationStatusText] = useState("准备生成计划...");
  const progressTimerRef = useRef<number | null>(null);

  useEffect(() => {
    const storedSession = readStoredSessionId();
    const nextSessionId = storedSession ?? createGuestSessionId();
    const demoScheduleFlag = readDemoScheduleFlag();

    setSessionId(nextSessionId);
    setHasDemoSchedule(demoScheduleFlag);
    persistSessionId(nextSessionId);
  }, [setHasDemoSchedule, setSessionId]);

  useEffect(() => {
    resetPlanOutputs();
  }, [resetPlanOutputs, sessionId]);

  const currentIndex = useMemo(() => Math.max(stepOrder.indexOf(currentStep), 0) + 1, [currentStep]);
  const currentMeta = stepMeta[currentStep];

  function startFakeGenerationProgress() {
    if (progressTimerRef.current) {
      window.clearInterval(progressTimerRef.current);
    }

    setShowGenerationOverlay(true);
    setGenerationProgress(6);
    setGenerationStatusText("AI 正在读取你的五项信息...");

    progressTimerRef.current = window.setInterval(() => {
      setGenerationProgress((prev) => {
        if (prev >= 80) {
          return 80;
        }

        const next = Math.min(prev + 4, 80);

        if (next >= 24 && next < 48) {
          setGenerationStatusText("AI 正在结合固定课表分析空档...");
        } else if (next >= 48 && next < 72) {
          setGenerationStatusText("AI 正在匹配体育场馆与训练时段...");
        } else if (next >= 72) {
          setGenerationStatusText("AI 正在整理本周计划结构...");
        }

        return next;
      });
    }, 240);
  }

  function stopFakeGenerationProgress(success: boolean) {
    if (progressTimerRef.current) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }

    if (!success) {
      setShowGenerationOverlay(false);
      setGenerationProgress(0);
      setGenerationStatusText("准备生成计划...");
      return;
    }

    setGenerationProgress(100);
    setGenerationStatusText("AI 规划成功！正在进入计划页面...");
  }

  async function handleContinue() {
    if (!sessionId || isSubmitting) {
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      if (currentStep === "step1_profile") {
        const response = await submitProfileStep({
          session_id: sessionId,
          gender: answers.profile?.gender ?? "男",
          height_cm: answers.profile?.height_cm ?? 175,
          weight_kg: answers.profile?.weight_kg ?? 70,
        });

        updateAnswers({
          profile: {
            gender: answers.profile?.gender ?? "男",
            height_cm: answers.profile?.height_cm ?? 175,
            weight_kg: answers.profile?.weight_kg ?? 70,
          },
        });
        setCurrentStep(response.next_step);
        return;
      }

      if (currentStep === "step2_goal") {
        const response = await submitGoalStep({
          session_id: sessionId,
          goal: answers.goal?.goal ?? "减脂",
          accept_muscle_loss: answers.goal?.goal === "减脂" ? answers.goal.accept_muscle_loss ?? "接受" : undefined,
        });

        updateAnswers({
          goal: {
            goal: answers.goal?.goal ?? "减脂",
            accept_muscle_loss: answers.goal?.goal === "减脂" ? answers.goal.accept_muscle_loss ?? "接受" : undefined,
          },
        });
        setCurrentStep(response.next_step);
        return;
      }

      if (currentStep === "step3_space_time") {
        persistDemoScheduleFlag(hasDemoSchedule);
        const response = await submitSpaceTimeStep({
          session_id: sessionId,
          frequency: answers.spaceTime?.frequency ?? "3-4次",
          duration: answers.spaceTime?.duration ?? "45-60分钟",
          preference: answers.spaceTime?.preference ?? "下课后",
          dorm_location: answers.spaceTime?.dorm_location ?? "西南区",
          schedule_image_url: hasDemoSchedule ? "https://demo.local/fixed_schedule.png" : null,
        });

        updateAnswers({
          spaceTime: {
            frequency: answers.spaceTime?.frequency ?? "3-4次",
            duration: answers.spaceTime?.duration ?? "45-60分钟",
            preference: answers.spaceTime?.preference ?? "下课后",
            dorm_location: answers.spaceTime?.dorm_location ?? "西南区",
            schedule_image_url: hasDemoSchedule ? "https://demo.local/fixed_schedule.png" : null,
          },
        });
        setCurrentStep(response.next_step);
        return;
      }

      if (currentStep === "step4_diet") {
        const response = await submitDietStep({
          session_id: sessionId,
          preferred_canteens: answers.diet?.preferred_canteens ?? ["听荔餐厅"],
          weekly_budget: answers.diet?.weekly_budget ?? "普通学生300-500元",
        });

        updateAnswers({
          diet: {
            preferred_canteens: answers.diet?.preferred_canteens ?? ["听荔餐厅"],
            weekly_budget: answers.diet?.weekly_budget ?? "普通学生300-500元",
          },
        });
        setCurrentStep(response.next_step);
        return;
      }

      if (currentStep === "step5_habits") {
        await submitHabitStep({
          session_id: sessionId,
          favorite_sport: answers.habits?.favorite_sport ?? "篮球",
          integrate_into_training: answers.habits?.integrate_into_training ?? true,
          favorite_sport_other: answers.habits?.favorite_sport_other,
        });

        updateAnswers({
          habits: {
            favorite_sport: answers.habits?.favorite_sport ?? "篮球",
            integrate_into_training: answers.habits?.integrate_into_training ?? true,
            favorite_sport_other: answers.habits?.favorite_sport_other,
          },
        });

        setCurrentStep("completed");

        const fixedSchedulePrompt = hasDemoSchedule
          ? `课表参考如下：${fixedScheduleSummary.join("；")}。`
          : "本次未附带固定课表。";
        const userNotePrompt = contextNote.trim() ? ` 用户补充：${contextNote.trim()}。` : "";

        try {
          startFakeGenerationProgress();
          const plan = await sendAssistantMessage({
            session_id: sessionId,
            message: `请根据我的五个信息点、体育场馆信息与固定课表自动生成本周训练计划，并给出可执行安排。${fixedSchedulePrompt}${userNotePrompt}`,
            is_initial_planning_turn: true,
          });

          if (!plan.plan_id || !plan.structured_plan) {
            throw new Error("assistant 首轮规划返回结果不完整，缺少计划数据。");
          }

          setPlanResult({
            planId: plan.plan_id,
            planText: plan.assistant_message,
            structuredPlan: plan.structured_plan,
          });
          stopFakeGenerationProgress(true);
          window.setTimeout(() => {
            router.push("/plan");
          }, 900);
        } catch (planError) {
          stopFakeGenerationProgress(false);
          setErrorMessage(extractErrorMessage(planError));
        }
      }
    } catch (error) {
      const message = extractErrorMessage(error);
      const serverStep = extractStepFromMessage(message);

      if (serverStep) {
        setCurrentStep(serverStep);
      }

      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function renderProfileStep() {
    const profileAnswer = answers.profile ?? {
      gender: "男" as const,
      height_cm: 175,
      weight_kg: 70,
    };

    return (
      <div className="space-y-5">
        <div>
          <p className="text-sm font-medium text-foreground">性别</p>
          <div className="mt-3 flex flex-wrap gap-3">
            {genderOptions.map((genderOption) => (
              <StepOptionButton
                key={genderOption}
                label={genderOption}
                active={profileAnswer.gender === genderOption}
                onClick={() => updateAnswers({ profile: { ...profileAnswer, gender: genderOption } })}
              />
            ))}
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">身高（cm）</label>
            <Input
              type="number"
              min={100}
              max={250}
              value={profileAnswer.height_cm}
              onChange={(event) =>
                updateAnswers({
                  profile: {
                    ...profileAnswer,
                    height_cm: Number(event.target.value) || 0,
                  },
                })
              }
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">体重（kg）</label>
            <Input
              type="number"
              min={20}
              max={250}
              value={profileAnswer.weight_kg}
              onChange={(event) =>
                updateAnswers({
                  profile: {
                    ...profileAnswer,
                    weight_kg: Number(event.target.value) || 0,
                  },
                })
              }
            />
          </div>
        </div>
      </div>
    );
  }

  function renderGoalStep() {
    const goalAnswer = answers.goal ?? {
      goal: undefined,
      accept_muscle_loss: undefined,
    };

    return (
      <div className="space-y-5">
        <div>
          <p className="text-sm font-medium text-foreground">本阶段主要目标</p>
          <div className="mt-3 flex flex-wrap gap-3">
            {goalOptions.map((goalOption) => (
              <StepOptionButton
                key={goalOption}
                label={goalOption}
                active={goalAnswer.goal === goalOption}
                onClick={() =>
                  updateAnswers({
                    goal: {
                      goal: goalOption,
                      accept_muscle_loss: goalOption === "减脂" ? goalAnswer.accept_muscle_loss ?? "接受" : undefined,
                    },
                  })
                }
              />
            ))}
          </div>
        </div>

        {goalAnswer.goal === "减脂" ? (
          <div>
            <p className="text-sm font-medium text-foreground">减脂时是否接受少量掉肌肉</p>
            <div className="mt-3 flex flex-wrap gap-3">
              {muscleLossOptions.map((muscleLossOption) => (
                <StepOptionButton
                  key={muscleLossOption}
                  label={muscleLossOption}
                  active={goalAnswer.accept_muscle_loss === muscleLossOption}
                  onClick={() =>
                    updateAnswers({
                      goal: {
                        ...goalAnswer,
                        accept_muscle_loss: muscleLossOption,
                      },
                    })
                  }
                />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  function renderSpaceTimeStep() {
    const spaceTimeAnswer = answers.spaceTime ?? {
      frequency: "3-4次" as const,
      duration: "45-60分钟" as const,
      preference: "下课后" as const,
      dorm_location: "西南区",
      schedule_image_url: hasDemoSchedule ? "https://demo.local/fixed_schedule.png" : null,
    };

    return (
      <div className="space-y-5">
        <div>
          <p className="text-sm font-medium text-foreground">每周训练频率</p>
          <div className="mt-3 flex flex-wrap gap-3">
            {frequencyOptions.map((frequencyOption) => (
              <StepOptionButton
                key={frequencyOption}
                label={frequencyOption}
                active={spaceTimeAnswer.frequency === frequencyOption}
                onClick={() => updateAnswers({ spaceTime: { ...spaceTimeAnswer, frequency: frequencyOption } })}
              />
            ))}
          </div>
        </div>

        <div>
          <p className="text-sm font-medium text-foreground">单次训练时长</p>
          <div className="mt-3 flex flex-wrap gap-3">
            {durationOptions.map((durationOption) => (
              <StepOptionButton
                key={durationOption}
                label={durationOption}
                active={spaceTimeAnswer.duration === durationOption}
                onClick={() => updateAnswers({ spaceTime: { ...spaceTimeAnswer, duration: durationOption } })}
              />
            ))}
          </div>
        </div>

        <div>
          <p className="text-sm font-medium text-foreground">更偏好的训练时间</p>
          <div className="mt-3 flex flex-wrap gap-3">
            {preferenceOptions.map((preferenceOption) => (
              <StepOptionButton
                key={preferenceOption}
                label={preferenceOption}
                active={spaceTimeAnswer.preference === preferenceOption}
                onClick={() => updateAnswers({ spaceTime: { ...spaceTimeAnswer, preference: preferenceOption } })}
              />
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">宿舍位置</label>
          <Input
            value={spaceTimeAnswer.dorm_location}
            onChange={(event) => updateAnswers({ spaceTime: { ...spaceTimeAnswer, dorm_location: event.target.value } })}
            placeholder="例如：西南区、荔园、南区"
          />
        </div>

        <div className="rounded-[24px] border border-dashed border-primary/25 bg-[#f7fbf9] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-foreground">固定课表（写死给 AI 分析）</p>
              <p className="mt-1 text-sm leading-6 text-muted">按你的要求，仅保留一份固定课表，不提供替代上传方案。</p>
            </div>
            <Badge tone="success">{hasDemoSchedule ? "已启用" : "未启用"}</Badge>
          </div>
          <ul className="mt-4 space-y-2 text-sm leading-6 text-muted">
            {fixedScheduleSummary.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button type="button" variant="secondary" onClick={() => setHasDemoSchedule(true)}>
              使用这份固定课表
            </Button>
            <Button type="button" variant="ghost" onClick={() => setHasDemoSchedule(false)}>
              本次不附带课表
            </Button>
          </div>
        </div>
      </div>
    );
  }

  function renderDietStep() {
    const dietAnswer = answers.diet ?? {
      preferred_canteens: ["听荔餐厅"],
      weekly_budget: "普通学生300-500元" as const,
    };

    function toggleCanteen(canteenName: string) {
      const nextCanteens = dietAnswer.preferred_canteens.includes(canteenName)
        ? dietAnswer.preferred_canteens.filter((item) => item !== canteenName)
        : [...dietAnswer.preferred_canteens, canteenName];

      updateAnswers({
        diet: {
          ...dietAnswer,
          preferred_canteens: nextCanteens,
        },
      });
    }

    function addCustomCanteen() {
      const normalizedName = canteenDraft.trim();
      if (!normalizedName || dietAnswer.preferred_canteens.includes(normalizedName)) {
        return;
      }

      updateAnswers({
        diet: {
          ...dietAnswer,
          preferred_canteens: [...dietAnswer.preferred_canteens, normalizedName],
        },
      });
      setCanteenDraft("");
    }

    return (
      <div className="space-y-5">
        <div>
          <p className="text-sm font-medium text-foreground">食堂 / 档口偏好</p>
          <div className="mt-3 flex flex-wrap gap-3">
            {commonCanteenOptions.map((canteenName) => (
              <StepOptionButton
                key={canteenName}
                label={canteenName}
                active={dietAnswer.preferred_canteens.includes(canteenName)}
                onClick={() => toggleCanteen(canteenName)}
              />
            ))}
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-[1fr_auto]">
          <Input value={canteenDraft} onChange={(event) => setCanteenDraft(event.target.value)} placeholder="补充其他食堂或常吃档口" />
          <Button type="button" variant="secondary" onClick={addCustomCanteen}>
            添加
          </Button>
        </div>

        <div>
          <p className="text-sm font-medium text-foreground">每周饮食预算</p>
          <div className="mt-3 flex flex-wrap gap-3">
            {budgetOptions.map((budgetOption) => (
              <StepOptionButton
                key={budgetOption}
                label={budgetOption}
                active={dietAnswer.weekly_budget === budgetOption}
                onClick={() => updateAnswers({ diet: { ...dietAnswer, weekly_budget: budgetOption } })}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  function renderHabitStep() {
    const habitAnswer = answers.habits ?? {
      favorite_sport: "篮球" as const,
      integrate_into_training: true,
      favorite_sport_other: "",
    };

    return (
      <div className="space-y-5">
        <div>
          <p className="text-sm font-medium text-foreground">最喜欢的运动</p>
          <div className="mt-3 flex flex-wrap gap-3">
            {sportOptions.map((sportOption) => (
              <StepOptionButton
                key={sportOption}
                label={sportOption}
                active={habitAnswer.favorite_sport === sportOption}
                onClick={() =>
                  updateAnswers({
                    habits: {
                      ...habitAnswer,
                      favorite_sport: sportOption,
                      favorite_sport_other: sportOption === "其他" ? habitAnswer.favorite_sport_other ?? "" : undefined,
                    },
                  })
                }
              />
            ))}
          </div>
        </div>

        {habitAnswer.favorite_sport === "其他" ? (
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">补充喜欢的运动</label>
            <Input
              value={habitAnswer.favorite_sport_other ?? ""}
              onChange={(event) =>
                updateAnswers({
                  habits: {
                    ...habitAnswer,
                    favorite_sport_other: event.target.value,
                  },
                })
              }
              placeholder="例如：飞盘、舞蹈、游泳"
            />
          </div>
        ) : null}

        <div>
          <p className="text-sm font-medium text-foreground">是否融入训练计划</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <StepOptionButton
              label="整合进去"
              active={habitAnswer.integrate_into_training}
              onClick={() => updateAnswers({ habits: { ...habitAnswer, integrate_into_training: true } })}
            />
            <StepOptionButton
              label="单独保留"
              active={!habitAnswer.integrate_into_training}
              onClick={() => updateAnswers({ habits: { ...habitAnswer, integrate_into_training: false } })}
            />
          </div>
        </div>
      </div>
    );
  }

  function renderCurrentStepForm() {
    if (currentStep === "step1_profile") {
      return renderProfileStep();
    }

    if (currentStep === "step2_goal") {
      return renderGoalStep();
    }

    if (currentStep === "step3_space_time") {
      return renderSpaceTimeStep();
    }

    if (currentStep === "step4_diet") {
      return renderDietStep();
    }

    if (currentStep === "step5_habits") {
      return renderHabitStep();
    }

    return <div className="rounded-2xl bg-background p-4 text-sm leading-6 text-muted">五个信息点已完成，当前正在等待进入计划页。</div>;
  }

  return (
    <main className="pb-16 pt-8 md:pt-10">
      {showGenerationOverlay ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/25 px-6 backdrop-blur-sm">
          <Card className="w-full max-w-2xl border-border/80 bg-white/95 shadow-soft">
            <CardContent className="space-y-6 p-6 md:p-8">
              <div className="space-y-3">
                <Badge tone="success">AI Planning</Badge>
                <div>
                  <h2 className="text-2xl font-semibold text-foreground">AI 正在为你生成计划</h2>
                  <p className="mt-2 text-sm leading-6 text-muted">正在结合你的信息、课表与场馆条件生成本周安排，请稍候。</p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="h-4 overflow-hidden rounded-full bg-secondary">
                  <div className="h-full rounded-full bg-primary transition-all duration-200" style={{ width: `${generationProgress}%` }} />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted">{generationStatusText}</span>
                  <span className="font-semibold text-foreground">{generationProgress}%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      <Container>
        <div className="space-y-6">
          <Card className="overflow-hidden border-border/80 bg-white/90">
            <CardContent className="space-y-8 p-6 md:p-8 lg:p-10">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div className="space-y-4">
                  <Badge>Frontend Planner Flow</Badge>
                  <div>
                    <h1 className="text-3xl font-bold text-foreground md:text-5xl">先采集五个信息点，再让 AI 自动出计划</h1>
                    <p className="mt-3 max-w-3xl text-sm leading-7 text-muted md:text-base">
                      当前前端只聚焦你要的主链路：用户进入页面后完成五项采集，AI 结合体育场馆信息和固定课表生成计划，再在计划页继续通过 tool 触发修改与可视化更新。
                    </p>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    ["五项采集", `${Math.min(currentIndex, 5)}/5`],
                    ["会话状态", sessionId ? "已创建" : "生成中"],
                    ["固定课表", hasDemoSchedule ? "启用" : "关闭"],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-3xl border border-border bg-background px-4 py-4">
                      <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
                      <p className="mt-2 text-lg font-semibold text-foreground">{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <ProgressSteps current={currentStep === "completed" ? 5 : currentIndex} total={5} />

              <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
                <Card className="border-border bg-[#f9fcfb] shadow-none">
                  <CardContent className="space-y-6 p-5 md:p-6">
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-primary">{currentMeta.metric}</p>
                      <h2 className="text-2xl font-semibold text-foreground">{currentMeta.title}</h2>
                      <p className="text-sm leading-7 text-muted">{currentMeta.prompt}</p>
                    </div>

                    <div className="rounded-[28px] border border-dashed border-primary/20 bg-white p-5">
                      <div className="mb-5 flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-foreground">当前采集卡</p>
                          <p className="mt-1 text-sm leading-6 text-muted">{currentMeta.hint}</p>
                        </div>
                        <Badge tone="muted">{currentMeta.shortTitle}</Badge>
                      </div>
                      {renderCurrentStepForm()}
                    </div>
                  </CardContent>
                </Card>

                <div className="space-y-6">
                  <Card className="bg-white/90">
                    <CardContent className="space-y-4 p-5">
                      <h2 className="text-lg font-semibold text-foreground">系统将收集的五个信息点</h2>
                      <ul className="space-y-3 text-sm leading-6 text-muted">
                        {stepOrder.map((step, index) => {
                          const active = step === currentStep;

                          return (
                            <li key={step} className={active ? "rounded-2xl bg-background px-4 py-3 font-medium text-foreground" : "px-4 py-1"}>
                              {index + 1}. {stepMeta[step].shortTitle}
                            </li>
                          );
                        })}
                      </ul>
                    </CardContent>
                  </Card>

                  <Card className="bg-white/90">
                    <CardContent className="space-y-4 p-5">
                      <h2 className="text-lg font-semibold text-foreground">生成逻辑说明</h2>
                      <ul className="space-y-3 text-sm leading-6 text-muted">
                        <li>• 五步信息逐步提交到真实后端接口</li>
                        <li>• 第三步可启用固定课表，供 AI 分析上课空档</li>
                        <li>• 第五步提交后立即触发计划生成</li>
                        <li>• 计划生成后自动跳转到可视化计划页</li>
                        <li>• 后续修改不走占位，而是继续调用 assistant 路由</li>
                      </ul>
                    </CardContent>
                  </Card>
                </div>
              </div>

              <div className="space-y-4">
                <label className="text-sm font-medium text-foreground">补充说明（会一并发给 AI）</label>
                <Textarea
                  value={contextNote}
                  onChange={(event) => setContextNote(event.target.value)}
                  placeholder="例如：膝盖容易不舒服；周三只能做低强度；希望多安排离宿舍近的场馆。"
                  className="min-h-[112px]"
                />
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <Button className="sm:min-w-[160px]" onClick={handleContinue} disabled={isSubmitting || !sessionId}>
                    {currentStep === "step5_habits" ? (isSubmitting ? "AI 生成中..." : "生成计划") : isSubmitting ? "提交中..." : "保存并继续"}
                  </Button>
                  <Button asChild variant="ghost">
                    <a href="/plan">直接查看计划页</a>
                  </Button>
                </div>
                {errorMessage ? <p className="text-sm text-[#b42318]">{errorMessage}</p> : null}
              </div>
            </CardContent>
          </Card>
        </div>
      </Container>
    </main>
  );
}
