const messages = {
  en: { open: "Open in new tab", download: "Download PDF", unavailable: "No download is available in this language. Please use the instructions below." },
  ar: { open: "فتح في علامة تبويب جديدة", download: "تنزيل ملف PDF", unavailable: "لا يتوفر ملف للتنزيل بهذه اللغة. يرجى اتباع التعليمات أدناه." },
  fr: { open: "Ouvrir dans un nouvel onglet", download: "Télécharger le PDF", unavailable: "Aucun téléchargement n’est disponible dans cette langue. Consultez les instructions ci-dessous." },
  de: { open: "In neuem Tab öffnen", download: "PDF herunterladen", unavailable: "In dieser Sprache steht kein Download zur Verfügung. Bitte lesen Sie die folgenden Anweisungen." },
  es: { open: "Abrir en una pestaña nueva", download: "Descargar PDF", unavailable: "No hay ninguna descarga disponible en este idioma. Consulta las instrucciones que aparecen a continuación." },
  tr: { open: "Yeni sekmede aç", download: "PDF indir", unavailable: "Bu dilde indirilebilir dosya yok. Lütfen aşağıdaki talimatları kullanın." },
  "zh-CN": { open: "在新标签页中打开", download: "下载 PDF", unavailable: "此语言暂无可下载文件。请参阅下方说明。" },
};
export function documentText(locale: string, key: keyof typeof messages.en) {
  const language = Object.prototype.hasOwnProperty.call(messages, locale) ? locale as keyof typeof messages : "en";
  return messages[language][key];
}
