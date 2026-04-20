document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  if (target.matches(".secret-box code")) {
    const value = target.innerText.trim();
    if (!value) return;

    navigator.clipboard.writeText(value).then(() => {
      target.dataset.copied = "1";
      const original = target.innerText;
      target.innerText = `${original} (copied)`;
      setTimeout(() => {
        target.innerText = original;
        delete target.dataset.copied;
      }, 1200);
    }).catch(() => {
      // no-op
    });
  }
});
