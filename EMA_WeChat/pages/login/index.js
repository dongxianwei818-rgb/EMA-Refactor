var onboarding = require("../../utils/onboarding");
var auth = require("../../utils/auth");

Page({
  data: {
    userName: "",
    psw: "",
    loading: false,
    error: "",
    pwdVisible: false,
    pwdLoading: false,
    pwdError: "",
    pwdUserName: "",
    pwdOld: "",
    pwdNew: "",
    pwdConfirm: "",
  },

  onShow: function () {
    if (auth.isLoggedIn()) {
      onboarding.resumeSessionWithOnboarding({ reLaunch: true }).catch(function () {});
    }
  },

  noop: function () {},

  onUserNameInput: function (e) {
    this.setData({ userName: e.detail.value, error: "" });
  },

  onPswInput: function (e) {
    this.setData({ psw: e.detail.value, error: "" });
  },

  onSubmit: function () {
    var that = this;
    if (that.data.loading) return;
    var userName = (that.data.userName || "").trim();
    var psw = that.data.psw || "";
    if (!userName || !psw) {
      that.setData({ error: "请输入用户名和密码" });
      return;
    }
    that.setData({ loading: true, error: "" });
    onboarding
      .loginWithPasswordAndRedirect(userName, psw, { reLaunch: true })
      .then(function () {
        that.setData({ loading: false, psw: "" });
      })
      .catch(function (err) {
        that.setData({
          loading: false,
          error: (err && err.message) || "登录失败",
        });
      });
  },

  openChangePwd: function () {
    this.setData({
      pwdVisible: true,
      pwdLoading: false,
      pwdError: "",
      pwdUserName: (this.data.userName || "").trim(),
      pwdOld: this.data.psw || "",
      pwdNew: "",
      pwdConfirm: "",
    });
  },

  closeChangePwd: function () {
    if (this.data.pwdLoading) return;
    this.setData({
      pwdVisible: false,
      pwdError: "",
      pwdOld: "",
      pwdNew: "",
      pwdConfirm: "",
    });
  },

  onPwdUserNameInput: function (e) {
    this.setData({ pwdUserName: e.detail.value, pwdError: "" });
  },

  onPwdOldInput: function (e) {
    this.setData({ pwdOld: e.detail.value, pwdError: "" });
  },

  onPwdNewInput: function (e) {
    this.setData({ pwdNew: e.detail.value, pwdError: "" });
  },

  onPwdConfirmInput: function (e) {
    this.setData({ pwdConfirm: e.detail.value, pwdError: "" });
  },

  onChangePassword: function () {
    var that = this;
    if (that.data.pwdLoading) return;
    var userName = (that.data.pwdUserName || "").trim();
    var oldPsw = that.data.pwdOld || "";
    var newPsw = (that.data.pwdNew || "").trim();
    var confirmPsw = (that.data.pwdConfirm || "").trim();
    if (!userName || !oldPsw || !newPsw) {
      that.setData({ pwdError: "请填写用户名、原密码和新密码" });
      return;
    }
    if (newPsw.length < 6) {
      that.setData({ pwdError: "新密码至少 6 位" });
      return;
    }
    if (newPsw !== confirmPsw) {
      that.setData({ pwdError: "两次输入的新密码不一致" });
      return;
    }
    that.setData({ pwdLoading: true, pwdError: "" });
    auth
      .changePassword(userName, oldPsw, newPsw)
      .then(function () {
        that.setData({
          pwdLoading: false,
          pwdVisible: false,
          pwdOld: "",
          pwdNew: "",
          pwdConfirm: "",
          userName: userName,
          psw: "",
          error: "",
        });
        wx.showToast({ title: "密码已修改", icon: "success" });
      })
      .catch(function (err) {
        that.setData({
          pwdLoading: false,
          pwdError: (err && err.message) || "修改密码失败",
        });
      });
  },
});
