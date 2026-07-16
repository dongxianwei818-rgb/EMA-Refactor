function pad(n) {
  return n < 10 ? "0" + n : String(n);
}

function formatClientAt(ms) {
  var d = ms ? new Date(ms) : new Date();
  return (
    d.getFullYear() +
    "-" +
    pad(d.getMonth() + 1) +
    "-" +
    pad(d.getDate()) +
    " " +
    pad(d.getHours()) +
    ":" +
    pad(d.getMinutes()) +
    ":" +
    pad(d.getSeconds())
  );
}

module.exports = {
  formatClientAt: formatClientAt,
};
