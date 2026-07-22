import { createRouter, createWebHistory } from "vue-router";
import { getToken, isAdmin } from "../api/auth";
import { hasConsent } from "../utils/consentState";
import { isResearchBound } from "../utils/ema";
import {
  ensureOnboardingSynced,
  hasLocalOnboardingCache,
  isOnboardingFresh,
} from "../utils/onboardingGate";

const MainLayout = () => import("../layouts/MainLayout.vue");
const TaskShell = () => import("../layouts/TaskShell.vue");
const Home = () => import("../views/Home.vue");
const Records = () => import("../views/Records.vue");
const TrendsEntry = () => import("../views/TrendsEntry.vue");
const AdminUserTrends = () => import("../views/admin/AdminUserTrends.vue");
const AdminRiskList = () => import("../views/admin/AdminRiskList.vue");
const AdminUserRisk = () => import("../views/admin/AdminUserRisk.vue");
const Chat = () => import("../views/Chat.vue");
const Resources = () => import("../views/Resources.vue");
const My = () => import("../views/My.vue");
const ProfileDetail = () => import("../views/my/ProfileDetail.vue");
const BehaviorDetail = () => import("../views/my/BehaviorDetail.vue");
const Users = () => import("../views/Users.vue");
const Consent = () => import("../views/Consent.vue");
const Login = () => import("../views/Login.vue");
const Baseline = () => import("../views/Baseline.vue");
const Questionnaire = () => import("../views/ema/Questionnaire.vue");
const Diary = () => import("../views/ema/Diary.vue");
const Voice = () => import("../views/ema/Voice.vue");
const Video = () => import("../views/ema/Video.vue");
const Steps = () => import("../views/ema/Steps.vue");

const routes = [
  { path: "/login", name: "login", component: Login, meta: { public: true } },
  {
    path: "/consent",
    name: "consent",
    component: Consent,
    meta: { requiresAuth: true },
  },
  {
    path: "/baseline",
    name: "baseline",
    component: Baseline,
    meta: { requiresAuth: true, requiresConsent: true },
  },
  {
    path: "/ema",
    component: TaskShell,
    meta: { requiresAuth: true, requiresConsent: true, requiresBaseline: true },
    children: [
      {
        path: "questionnaire",
        name: "ema-questionnaire",
        component: Questionnaire,
      },
      { path: "diary", name: "ema-diary", component: Diary },
      { path: "voice", name: "ema-voice", component: Voice },
      { path: "video", name: "ema-video", component: Video },
      { path: "steps", name: "ema-steps", component: Steps },
    ],
  },
  {
    path: "/",
    component: MainLayout,
    redirect: "/home",
    children: [
      {
        path: "home",
        name: "home",
        component: Home,
        meta: { requiresAuth: true, requiresConsent: true, title: "首页" },
      },
      {
        path: "records",
        name: "records",
        component: Records,
        meta: { requiresAuth: true, requiresConsent: true, title: "打卡记录" },
      },
      {
        path: "trends",
        name: "trends",
        component: TrendsEntry,
        meta: { requiresAuth: true, requiresConsent: true, title: "趋势分析" },
      },
      {
        path: "trends/users/:userId",
        name: "admin-user-trends",
        component: AdminUserTrends,
        meta: {
          requiresAuth: true,
          requiresAdmin: true,
          title: "用户趋势详情",
        },
      },
      {
        path: "risk",
        name: "risk",
        component: AdminRiskList,
        meta: { requiresAuth: true, requiresAdmin: true, title: "风险预警" },
      },
      {
        path: "risk/users/:userId",
        name: "admin-user-risk",
        component: AdminUserRisk,
        meta: {
          requiresAuth: true,
          requiresAdmin: true,
          title: "用户风险预警详情",
        },
      },
      {
        path: "chat",
        name: "chat",
        component: Chat,
        meta: { requiresAuth: true, requiresConsent: true, title: "对话" },
      },
      {
        path: "resources",
        name: "resources",
        component: Resources,
        meta: { requiresAuth: true, requiresConsent: true, title: "资源分享" },
      },
      {
        path: "users",
        name: "users",
        component: Users,
        meta: { requiresAuth: true, requiresAdmin: true, title: "用户管理" },
      },
      {
        path: "my",
        name: "my",
        component: My,
        meta: { requiresAuth: true, requiresConsent: true, title: "我的信息" },
      },
      {
        path: "my/profile",
        name: "my-profile",
        component: ProfileDetail,
        meta: {
          requiresAuth: true,
          requiresConsent: true,
          title: "基本信息详情",
        },
      },
      {
        path: "my/behavior",
        name: "my-behavior",
        component: BehaviorDetail,
        meta: {
          requiresAuth: true,
          requiresConsent: true,
          title: "使用行为详情",
        },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

function routeMeta(to) {
  return {
    public: to.matched.some((r) => r.meta.public),
    requiresAuth: to.matched.some((r) => r.meta.requiresAuth),
    requiresConsent: to.matched.some((r) => r.meta.requiresConsent),
    requiresAdmin: to.matched.some((r) => r.meta.requiresAdmin),
    requiresBaseline: to.matched.some((r) => r.meta.requiresBaseline),
  };
}

router.beforeEach(async (to) => {
  const meta = routeMeta(to);

  if (meta.public || to.name === "login") {
    if (to.name === "login" && getToken()) {
      return { path: isAdmin() ? "/trends" : "/home", replace: true };
    }
    return true;
  }

  const needsAuth =
    meta.requiresAuth ||
    meta.requiresConsent ||
    meta.requiresAdmin ||
    meta.requiresBaseline;
  if (needsAuth && !getToken()) {
    return { path: "/login", query: { redirect: to.fullPath }, replace: true };
  }

  if (meta.requiresAdmin && !isAdmin()) {
    return { path: "/home", replace: true };
  }

  // 管理员跳过知情同意与基线；默认落到趋势分析
  if (isAdmin()) {
    if (to.path === "/" || to.name === "home") {
      return { path: "/trends", replace: true };
    }
    return true;
  }

  // 本地已明确同意+基线时，绝不阻塞导航；后台静默刷新即可
  const localReady = hasConsent() && isResearchBound();
  if ((meta.requiresConsent || meta.requiresBaseline) && !localReady) {
    const needSync = !isOnboardingFresh() || !hasLocalOnboardingCache();
    if (needSync) {
      await ensureOnboardingSynced();
    }
  } else if (
    (meta.requiresConsent || meta.requiresBaseline) &&
    !isOnboardingFresh()
  ) {
    ensureOnboardingSynced();
  }

  if (meta.requiresConsent && to.name !== "consent") {
    if (!hasConsent()) {
      return { path: "/consent", replace: true };
    }
  }

  const needsBaseline =
    meta.requiresBaseline ||
    (meta.requiresConsent &&
      !["consent", "baseline"].includes(String(to.name)));
  if (needsBaseline && !isResearchBound() && to.name !== "baseline") {
    return { path: "/baseline", replace: true };
  }

  return true;
});

export default router;
