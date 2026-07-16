var C = require("./constants");

function formatBaselineTime(ts) {
  if (!ts) return "";
  var d = new Date(ts);
  return d.getFullYear() + "年" + (d.getMonth() + 1) + "月" + d.getDate() + "日";
}

function collectSectionRows(section, profile) {
  var rows = [];
  if (section.fields) {
    section.fields.forEach(function (f) {
      var val = profile[f.id];
      if (val !== undefined && val !== "") {
        rows.push({ label: f.label, value: val });
      }
    });
  }
  if (section.items) {
    section.items.forEach(function (q) {
      var val = profile[q.id];
      if (val !== undefined && val !== "") {
        rows.push({ label: q.label, value: val });
      }
    });
  }
  return rows;
}

/** 「我的」页摘要：仅已填写的基本信息（不含研究编号） */
function buildBasicSummary(profile) {
  var section = null;
  for (var i = 0; i < C.BASELINE_SECTIONS.length; i++) {
    if (C.BASELINE_SECTIONS[i].id === "basic") {
      section = C.BASELINE_SECTIONS[i];
      break;
    }
  }
  if (!section) return [];
  return collectSectionRows(section, profile).filter(function (r) {
    return r.label !== "研究编号";
  });
}

/** 详情页：所有已填写的基本信息与基线测评 */
function buildProfileDetailSections(profile) {
  var sections = [];
  C.BASELINE_SECTIONS.forEach(function (section) {
    var rows = collectSectionRows(section, profile);
    if (rows.length) {
      sections.push({ id: section.id, title: section.title, rows: rows });
    }
  });
  return sections;
}

module.exports = {
  formatBaselineTime: formatBaselineTime,
  buildBasicSummary: buildBasicSummary,
  buildProfileDetailSections: buildProfileDetailSections,
};
