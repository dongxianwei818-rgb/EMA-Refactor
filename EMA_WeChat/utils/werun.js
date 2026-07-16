var C = require('./constants');
var sync = require('./sync');

function fetchTodaySteps(code, encryptedData, iv) {
  return new Promise(function (resolve, reject) {
    if (!C.API_BASE_URL) {
      reject(new Error('API_BASE_URL 未配置'));
      return;
    }
    var token = sync.getToken();
    if (!token) {
      reject(new Error('请先登录后再获取步数'));
      return;
    }
    wx.request({
      url: C.API_BASE_URL.replace(/\/$/, '') + '/steps/werun',
      method: 'POST',
      header: {
        'content-type': 'application/json',
        Authorization: 'Bearer ' + token,
      },
      data: {
        code: code,
        encryptedData: encryptedData,
        iv: iv,
      },
      success: function (res) {
        var body = res.data || {};
        if (res.statusCode === 200 && body.code === 0 && body.data) {
          resolve(body.data);
          return;
        }
        var msg = body.message;
        if (!msg && body.detail) {
          msg = typeof body.detail === 'string' ? body.detail : (body.detail[0] && body.detail[0].msg) || '解密步数失败';
        }
        reject(new Error(msg || '解密步数失败'));
      },
      fail: reject,
    });
  });
}

module.exports = {
  fetchTodaySteps: fetchTodaySteps,
};
