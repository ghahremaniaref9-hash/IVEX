// "Sizi arayalım" form: inline validation, sends to Netlify Forms (which emails the
// team), then offers to send the same details on WhatsApp.

const WHATSAPP_NUMBER = "905010623794";

type Rule = (el: HTMLInputElement) => string;

const RULES: Record<string, Rule> = {
  ad: (el) => (el.value.trim().length >= 2 ? "" : "Adınızı yazın."),
  soyad: (el) => (el.value.trim().length >= 2 ? "" : "Soyadınızı yazın."),
  telefon: (el) => (el.value.replace(/\D/g, "").length >= 10 ? "" : "Geçerli bir telefon numarası yazın."),
  eposta: (el) => (/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(el.value.trim()) ? "" : "Geçerli bir e-posta adresi yazın."),
  onay: (el) => (el.checked ? "" : "Devam etmek için onay vermeniz gerekiyor."),
};

function setup(form: HTMLFormElement) {
  const panel = form.parentElement;
  const sent = panel?.querySelector<HTMLElement>("[data-sent]");
  const status = form.querySelector<HTMLElement>("[data-status]");
  const submit = form.querySelector<HTMLButtonElement>("button[type='submit']");
  const submitLabel = form.querySelector<HTMLElement>("[data-submit-label]");
  if (!sent || !status || !submit || !submitLabel) return;
  const idleLabel = submitLabel.textContent ?? "";

  const input = (name: string) => form.elements.namedItem(name) as HTMLInputElement | null;

  const check = (name: string) => {
    const el = input(name);
    const rule = RULES[name];
    if (!el || !rule) return true;
    const message = rule(el);
    const err = document.getElementById(`${el.id}-err`);
    if (err) err.textContent = message;
    if (message) el.setAttribute("aria-invalid", "true");
    else el.removeAttribute("aria-invalid");
    return message === "";
  };

  // Validate a field once the visitor leaves it, then live while they fix it.
  Object.keys(RULES).forEach((name) => {
    const el = input(name);
    if (!el) return;
    el.addEventListener("blur", () => {
      if (el.value || el.type === "checkbox") check(name);
    });
    el.addEventListener("input", () => {
      if (el.hasAttribute("aria-invalid")) check(name);
    });
    el.addEventListener("change", () => {
      if (el.type === "checkbox") check(name);
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    status.textContent = "";
    const results = Object.keys(RULES).map((name) => [name, check(name)] as const);
    const firstBad = results.find(([, ok]) => !ok);
    if (firstBad) {
      status.textContent = "Lütfen işaretli alanları kontrol edin.";
      input(firstBad[0])?.focus();
      return;
    }

    const body = new URLSearchParams();
    for (const [key, value] of new FormData(form)) {
      if (typeof value === "string") body.append(key, value.trim());
    }

    submit.setAttribute("aria-busy", "true");
    submit.disabled = true;
    submitLabel.textContent = "Gönderiliyor…";
    try {
      const res = await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showSent();
    } catch {
      status.textContent = "Form gönderilemedi. Lütfen tekrar deneyin ya da ";
      const link = document.createElement("a");
      link.href = `https://wa.me/${WHATSAPP_NUMBER}`;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "WhatsApp'tan yazın";
      status.append(link, ".");
    } finally {
      submit.removeAttribute("aria-busy");
      submit.disabled = false;
      submitLabel.textContent = idleLabel;
    }
  });

  function showSent() {
    const val = (name: string) => input(name)?.value.trim() ?? "";
    const name = val("ad");
    const nameSlot = sent!.querySelector<HTMLElement>("[data-sent-name]");
    if (nameSlot) nameSlot.textContent = name ? `, ${name}` : "";
    const text = [
      "Merhaba, web sitenizden başvuru yapıyorum.",
      `Ad Soyad: ${name} ${val("soyad")}`,
      `Telefon: ${val("telefon")}`,
      `E-posta: ${val("eposta")}`,
    ].join("\n");
    const wa = sent!.querySelector<HTMLAnchorElement>("[data-sent-wa]");
    if (wa) wa.href = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(text)}`;
    form.hidden = true;
    sent!.hidden = false;
    sent!.querySelector<HTMLElement>(".ivx-sent__title")?.focus();
  }
}

document.querySelectorAll<HTMLFormElement>("form[data-ivx-form]").forEach(setup);
