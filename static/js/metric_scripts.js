(function(){
  if (!("sendBeacon" in navigator)) return;
  const body = JSON.stringify({
    lang: navigator.language || "",
    tz_offset: new Date().getTimezoneOffset(),
    screen_w: screen && screen.width ? screen.width : null,
    screen_h: screen && screen.height ? screen.height : null
  });
  navigator.sendBeacon("{% url 'metrics_collect' %}", new Blob([body], {type: "application/json"}));
})();

