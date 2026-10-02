import type { Context } from "@netlify/functions";

// Runs on every verified Netlify Forms submission (spam-filtered) and forwards the
// "Sizi arayalım" details to the agency's WhatsApp through the CallMeBot API.
// Needs CALLMEBOT_APIKEY (and optionally WHATSAPP_PHONE) set as environment variables.

type Submission = {
  payload?: {
    form_name?: string;
    created_at?: string;
    data?: Record<string, string | undefined>;
  };
};

export default async (req: Request, _context: Context) => {
  const apikey = Netlify.env.get("CALLMEBOT_APIKEY");
  const phone = Netlify.env.get("WHATSAPP_PHONE") ?? "+905010623794";
  if (!apikey) {
    console.warn("CALLMEBOT_APIKEY is not set; WhatsApp notification skipped.");
    return;
  }

  const { payload } = (await req.json()) as Submission;
  if (payload?.form_name !== "basvuru") return;

  const text = buildMessage(payload.data ?? {}, payload.created_at);
  const url = `https://api.callmebot.com/whatsapp.php?${new URLSearchParams({ phone, text, apikey })}`;
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(10_000) });
    if (!res.ok) console.error(`WhatsApp notification failed: HTTP ${res.status}`);
  } catch (error) {
    console.error("WhatsApp notification failed:", error);
  }
};

function buildMessage(data: Record<string, string | undefined>, createdAt?: string): string {
  const clean = (v: string | undefined) => (v ?? "").replace(/\s+/g, " ").trim().slice(0, 120);
  const name = `${clean(data.ad)} ${clean(data.soyad)}`.trim();
  const tel = clean(data.telefon);
  const lines = [
    "*Yeni başvuru* (ivexco.com.tr)",
    `Ad Soyad: ${name || "-"}`,
    `Telefon: ${tel || "-"}`,
    `E-posta: ${clean(data.eposta) || "-"}`,
  ];
  const wa = whatsappLink(tel);
  if (wa) lines.push(`WhatsApp: ${wa}`);
  const when = createdAt ? new Date(createdAt) : new Date();
  if (!Number.isNaN(when.getTime())) {
    lines.push(
      `Tarih: ${new Intl.DateTimeFormat("tr-TR", { timeZone: "Europe/Istanbul", dateStyle: "short", timeStyle: "short" }).format(when)}`,
    );
  }
  return lines.join("\n");
}

// Turkish numbers as typed in the form (0532..., 532..., +90 532...) -> wa.me link.
function whatsappLink(raw: string): string | null {
  let digits = raw.replace(/\D/g, "");
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (digits.length === 11 && digits.startsWith("0")) digits = `90${digits.slice(1)}`;
  if (digits.length === 10 && digits.startsWith("5")) digits = `90${digits}`;
  return digits.length >= 11 ? `https://wa.me/${digits}` : null;
}
