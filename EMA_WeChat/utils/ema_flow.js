/**
 * EMA 打卡步骤提交：全屏 loading，待后端交互完成后再跳转下一步。
 */
var ema = require("./ema");

var HOME_URL = "/pages/home/index";

function showSubmitLoading(title) {
  wx.showLoading({
    title: title || "提交中…",
    mask: true,
  });
}

function hideSubmitLoading() {
  try {
    wx.hideLoading();
  } catch (e) {
    /* ignore */
  }
}

/**
 * @param {object} options
 * @param {object} [options.page] 页面实例，用于 setData({ submitting })
 * @param {string} [options.title] loading 文案
 * @param {function} options.submit 返回 Promise 的提交函数
 * @param {string} [options.successToast] 成功后 toast
 * @param {string} [options.successIcon] toast icon，默认 success
 * @param {boolean} [options.goNext=true] 成功后是否跳转下一任务
 * @param {number} [options.delay=400] 跳转延迟 ms
 * @param {function} [options.onSuccess] 成功回调（若提供则不再自动 goNext）
 * @param {function} [options.onError] 失败回调
 */
function runStepSubmit(options) {
  var page = options.page;
  var goNext = options.goNext !== false;

  if (page && page.setData) {
    page.setData({ submitting: true });
  }
  showSubmitLoading(options.title || "提交中…");

  return Promise.resolve()
    .then(function () {
      return options.submit();
    })
    .then(function (result) {
      hideSubmitLoading();
      if (page && page.setData) {
        page.setData({ submitting: false });
      }
      if (options.successToast) {
        wx.showToast({
          title: options.successToast,
          icon: options.successIcon || "success",
        });
      }
      if (options.onSuccess) {
        return options.onSuccess(result);
      }
      if (goNext) {
        navigateNext(options.delay);
      }
      return result;
    })
    .catch(function (err) {
      hideSubmitLoading();
      if (page && page.setData) {
        page.setData({ submitting: false });
      }
      if (options.onError) {
        options.onError(err);
        return;
      }
      wx.showToast({
        title: (err && err.message) || "提交失败",
        icon: "none",
      });
    });
}

function navigateNext(delay) {
  var ms = delay === undefined ? 400 : delay;
  var next = ema.getNextTaskRoute();
  setTimeout(function () {
    if (next) wx.redirectTo({ url: next });
    else wx.switchTab({ url: HOME_URL });
  }, ms);
}

function goHome(delay) {
  var ms = delay === undefined ? 400 : delay;
  setTimeout(function () {
    wx.switchTab({ url: HOME_URL });
  }, ms);
}

module.exports = {
  runStepSubmit: runStepSubmit,
  navigateNext: navigateNext,
  goHome: goHome,
  showSubmitLoading: showSubmitLoading,
  hideSubmitLoading: hideSubmitLoading,
};
