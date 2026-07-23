var C = require("./constants");

function formatBaselineTime(ts) {
  if (!ts) return "";
  var d = new Date(ts);
  return d.getFullYear() + "年" + (d.getMonth() + 1) + "月" + d.getDate() + "日";
}

function collectSectionRows(section, profile) {
  var rows = [];
  var toneIndex = 0;
  if (section.fields) {
    section.fields.forEach(function (f) {
      var val = profile[f.id];
      if (val !== undefined && val !== null && val !== "") {
        rows.push({ id: f.id, label: f.label, value: val });
        toneIndex++;
      }
    });
  }
  if (section.items) {
    section.items.forEach(function (q) {
      var val = profile[q.id];
      if (val !== undefined && val !== null && val !== "") {
        // 问卷题项用循环配色，避免无匹配 id 时无胶囊色
        rows.push({
          id: "tone" + (toneIndex % 10),
          label: q.label,
          value: val,
        });
        toneIndex++;
      }
    });
  }
  return rows;
}

/** 「我的」页摘要：研究编号 + 年龄/年级等基本信息（含 id 供胶囊配色） */
function buildBasicSummary(profile) {
  var section = null;
  for (var i = 0; i < C.BASELINE_SECTIONS.length; i++) {
    if (C.BASELINE_SECTIONS[i].id === "basic") {
      section = C.BASELINE_SECTIONS[i];
      break;
    }
  }
  if (!section || !section.fields) return [];
  var order = [
    "researchId",
    "age",
    "grade",
    "major",
    "gender",
    "onlyChild",
    "housing",
  ];
  var byId = {};
  section.fields.forEach(function (f) {
    byId[f.id] = f;
  });
  var normalized = Object.assign({}, profile, {
    researchId: profile.researchId || profile.research_id || "",
  });
  var rows = [];
  order.forEach(function (id) {
    var field = byId[id];
    if (!field) return;
    var val = normalized[id];
    if (val !== undefined && val !== null && val !== "") {
      rows.push({ id: id, label: field.label, value: val });
    }
  });
  return rows;
}

/** 详情页：所有已填写的基本信息与基线测评 */
function buildProfileDetailSections(profile) {
  var sections = [];
  var normalized = Object.assign({}, profile, {
    researchId: profile.researchId || profile.research_id || "",
  });
  C.BASELINE_SECTIONS.forEach(function (section) {
    var rows = collectSectionRows(section, normalized);
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
