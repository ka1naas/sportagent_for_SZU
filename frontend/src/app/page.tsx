import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Container } from "@/components/ui/container";
import { SectionHeading } from "@/components/ui/section-heading";

const features = [
  {
    title: "五步对话规划",
    description: "像聊天一样收集目标、时空约束和预算，而不是把用户扔进一长串表单。",
  },
  {
    title: "不满意就直接修改",
    description: "生成计划后，用户可以直接说“这样不行”，系统再对训练安排做结构化调整。",
  },
  {
    title: "现在能不能练",
    description: "结合天气和场馆状态，快速回答“现在适不适合去训练”这种高频问题。",
  },
];

const highlights = [
  "对话式规划，不做后台感表单",
  "先支持课表上传占位，保证演示链路完整",
  "训练修改、天气判断、普通提问三类消息分流",
];

export default function HomePage() {
  return (
    <main className="pb-20 pt-8 md:pt-10">
      <Container>
        <section className="overflow-hidden rounded-[36px] border border-border/80 bg-white/90 shadow-soft backdrop-blur">
          <div className="grid gap-10 px-6 py-8 md:px-10 md:py-10 lg:grid-cols-[1.2fr_0.8fr] lg:px-14 lg:py-14">
            <div className="space-y-8">
              <div className="flex items-center justify-between gap-4">
                <div className="inline-flex rounded-full bg-secondary px-4 py-2 text-sm font-medium text-secondary-foreground">
                  Campus Fitness Scheduler MVP
                </div>
                <div className="hidden rounded-full border border-border bg-white px-4 py-2 text-sm text-muted md:block">
                  对话规划 · 训练修改 · 天气判断
                </div>
              </div>

              <div className="space-y-5">
                <h1 className="max-w-4xl text-4xl font-bold tracking-tight text-foreground md:text-6xl md:leading-[1.1]">
                  校园智能健身规划助手
                </h1>
                <p className="max-w-2xl text-base leading-8 text-muted md:text-lg">
                  用五步对话收集你的目标与约束，生成校园场景下的训练计划；觉得不合适就直接改，想知道现在能不能去训练就即时看天气与场馆状态。
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <Button asChild href="/planner" size="lg" className="min-w-[160px]">
                  开始规划
                </Button>
                <Button asChild href="/plan" variant="secondary" size="lg" className="min-w-[160px]">
                  查看计划原型
                </Button>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                {highlights.map((item) => (
                  <div key={item} className="rounded-2xl border border-border bg-background px-4 py-4 text-sm leading-6 text-foreground">
                    {item}
                  </div>
                ))}
              </div>
            </div>

            <Card className="border-white/50 bg-[#f7fbf9]">
              <CardContent className="space-y-5 p-6 md:p-7">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-primary">演示主链路</p>
                    <h2 className="mt-2 text-2xl font-semibold text-foreground">从对话到行动建议</h2>
                  </div>
                  <div className="rounded-full bg-white px-3 py-2 text-sm text-muted shadow-sm">MVP</div>
                </div>

                <div className="space-y-3">
                  {[
                    "1. 五步对话完成信息采集",
                    "2. 课表上传先用占位方案写死",
                    "3. 生成结构化训练计划",
                    "4. 用户不满意时直接修改训练",
                    "5. 即时回答现在能不能训练",
                  ].map((item) => (
                    <div key={item} className="rounded-2xl border border-border bg-white px-4 py-4 text-sm leading-6 text-foreground">
                      {item}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="mt-16 space-y-8">
          <SectionHeading
            eyebrow="Why this MVP"
            title="聚焦真实可演示的三大价值"
            description="先把真正能联调跑通的用户价值做扎实：对话规划、可修改计划、天气训练判断。"
          />

          <div className="grid gap-5 lg:grid-cols-3">
            {features.map((feature) => (
              <Card key={feature.title} className="bg-white/90">
                <CardContent className="space-y-3">
                  <div className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary text-sm font-semibold text-secondary-foreground">
                    {feature.title.slice(0, 2)}
                  </div>
                  <h3 className="text-xl font-semibold text-foreground">{feature.title}</h3>
                  <p className="text-sm leading-7 text-muted">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </Container>
    </main>
  );
}
