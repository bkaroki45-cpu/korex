(() => {
  const now = () => Date.now();
  const format = (milliseconds) => {
    const seconds = Math.max(0, Math.ceil(milliseconds / 1000));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  };
  const tick = () => {
    document.querySelectorAll("[data-countdown]").forEach((node) => {
      const remaining = new Date(node.dataset.countdown).getTime() - now();
      node.textContent = remaining > 0 ? format(remaining) : "expired";
    });
    document.querySelectorAll("[data-resend-button]").forEach((button) => {
      const remaining = new Date(button.dataset.resendAt).getTime() - now();
      const status = button.parentElement.querySelector("[data-resend-status]");
      button.disabled = remaining > 0;
      if (status) status.textContent = remaining > 0 ? ` Available in ${format(remaining)}.` : " You can request a new code now.";
    });
  };
  tick(); window.setInterval(tick, 1000);
})();
