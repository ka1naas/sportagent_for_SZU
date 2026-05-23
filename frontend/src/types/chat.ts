export type StepName =
  | "step1_profile"
  | "step2_goal"
  | "step3_space_time"
  | "step4_diet"
  | "step5_habits"
  | "completed";

export type ChatStepResponse = {
  session_id: string;
  current_step: StepName;
  next_step: StepName;
  message: string;
  data: Record<string, unknown>;
};

export type ProfileStepPayload = {
  session_id: string;
  gender: "男" | "女" | "第三性别";
  height_cm: number;
  weight_kg: number;
};

export type GoalStepPayload = {
  session_id: string;
  goal: "减脂" | "增肌" | "力量" | "爆发力" | "耐力";
  accept_muscle_loss?: "接受" | "不接受";
};

export type SpaceTimeStepPayload = {
  session_id: string;
  frequency: "1-2次" | "3-4次" | "5次以上";
  duration: "30分钟内" | "45-60分钟" | "1小时以上";
  preference: "上课前" | "下课后" | "无所谓";
  dorm_location: string;
  schedule_image_url?: string | null;
};

export type DietStepPayload = {
  session_id: string;
  preferred_canteens: string[];
  weekly_budget: "极限穷鬼<300元" | "普通学生300-500元" | "宽裕>500元";
};

export type HabitStepPayload = {
  session_id: string;
  favorite_sport: "篮球" | "骑行" | "跑步" | "羽毛球" | "健身" | "不爱运动" | "其他";
  favorite_sport_other?: string;
  integrate_into_training: boolean;
};
