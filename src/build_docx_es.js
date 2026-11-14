const fs = require("fs");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, BorderStyle,
  Footer, PageNumber, LevelFormat, SectionType, ShadingType, HeadingLevel } = D;
const items = JSON.parse(fs.readFileSync("reports/es_items.json", "utf8"));
const FONT = "Times New Roman";

function runs(text, base = {}) {
  text = text.replace(/<br\/>/g, "\u0001");
  const out = []; let b = false, i = false, mono = false;
  const parts = text.split(/(<\/?b>|<\/?i>|<font name='Mono'>|<\/font>)/);
  for (const p of parts) {
    if (p === "<b>") b = true; else if (p === "</b>") b = false;
    else if (p === "<i>") i = true; else if (p === "</i>") i = false;
    else if (p === "<font name='Mono'>") mono = true; else if (p === "</font>") mono = false;
    else if (p) {
      const t = p.replace(/&amp;/g, "&").replace(/&gt;/g, ">").replace(/&lt;/g, "<");
      t.split("\u0001").forEach((seg, k) => {
        if (k > 0) out.push(new TextRun({ break: 1, ...base }));
        if (seg) out.push(new TextRun({ text: seg, bold: b || base.bold, italics: i || base.italics, font: mono ? "Consolas" : FONT,
          size: mono ? (base.size ? base.size - 1 : 16) : base.size }));
      });
    }
  }
  return out;
}
const J = AlignmentType.JUSTIFIED, C = AlignmentType.CENTER, L = AlignmentType.LEFT;
const sp = (before, after, line) => ({ before, after, line: line || 252, lineRule: D.LineRuleType.AUTO });
function para(it) {
  const st = it.style;
  if (st === "title") return new Paragraph({ alignment: C, spacing: sp(0, 100, 240), children: runs(it.text, { size: 34, bold: true }) });
  if (st === "auth") return new Paragraph({ alignment: C, spacing: sp(0, 20, 240), children: runs(it.text, { size: 19 }) });
  if (st === "abs" || st === "kw") return new Paragraph({ alignment: J, spacing: sp(40, 60), children: runs(it.text, { size: 18, bold: true }) });
  if (st === "cell") return new Paragraph({ alignment: J, spacing: sp(0, 80), children: runs(it.text, { size: 14 }) });
  return new Paragraph({ alignment: J, spacing: sp(0, 70), children: runs(it.text, { size: 18 }) });
}
const bdr = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
function tableOf(it) {
  const tot = 4896; const raw = it.widths.reduce((a, b) => a + b, 0);
  let w = it.widths.map(x => Math.floor(x / raw * tot)); w[w.length - 1] += tot - w.reduce((a, b) => a + b, 0);
  const rows = it.rows.map((r, ri) => new TableRow({ tableHeader: ri === 0, cantSplit: true, children: r.map((c, ci) => new TableCell({
    width: { size: w[ci], type: WidthType.DXA },
    margins: { top: 20, bottom: 20, left: 40, right: 40 },
    borders: { top: ri === 0 ? { ...bdr, size: 8 } : none, bottom: ri === 0 ? bdr : (ri === it.rows.length - 1 ? { ...bdr, size: 8 } : none), left: none, right: none },
    children: [new Paragraph({ alignment: L, spacing: sp(0, 0, 220), children: runs(c, { size: 14, bold: ri === 0 }) })] })) }));
  return [
    new Paragraph({ alignment: C, keepNext: true, spacing: sp(60, 0, 220), children: runs(it.title, { size: 15 }) }),
    new Paragraph({ alignment: C, keepNext: true, spacing: sp(0, 40, 220), children: runs(it.caption, { size: 15 }) }),
    new Table({ width: { size: tot, type: WidthType.DXA }, columnWidths: w, rows }),
    new Paragraph({ spacing: sp(0, 80), children: [] })];
}
function build(list) {
  const out = [];
  for (const it of list) {
    if (it.t === "p") out.push(para(it));
    else if (it.t === "h1") out.push(new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: C, keepNext: true, spacing: sp(140, 70, 240),
      children: [new TextRun({ text: it.text.toUpperCase(), font: FONT, size: 18 })] }));
    else if (it.t === "h2") out.push(new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, spacing: sp(80, 40, 240),
      children: [new TextRun({ text: it.text, font: FONT, size: 18, italics: true })] }));
    else if (it.t === "bullet") out.push(new Paragraph({ numbering: { reference: "bul", level: 0 }, alignment: J, spacing: sp(0, 30), children: runs(it.text, { size: 18 }) }));
    else if (it.t === "fig") {
      const wpx = Math.round(it.w * 96), hpx = Math.round(it.h * 96);
      out.push(new Paragraph({ alignment: C, keepNext: true, spacing: sp(40, 20, 240), children: [new ImageRun({ type: "png", data: fs.readFileSync(it.path),
        transformation: { width: wpx, height: hpx }, altText: { title: it.caption, description: it.caption, name: "figura" } })] }));
      out.push(new Paragraph({ alignment: J, spacing: sp(0, 100, 220), children: runs(it.caption, { size: 15 }) }));
    } else if (it.t === "table") out.push(...tableOf(it));
    else if (it.t === "ref") out.push(new Paragraph({ alignment: J, spacing: sp(0, 30, 220), indent: { left: 280, hanging: 280 }, children: runs(it.text, { size: 15 }) }));
  }
  return out;
}
const idx = items.findIndex(x => x.t === "framebreak");
const head = items.slice(0, idx), rest = items.slice(idx + 1);
const page = { size: { width: 12240, height: 15840 }, margin: { top: 940, bottom: 940, left: 890, right: 890 } };
const footer = new Footer({ children: [new Paragraph({ alignment: C, children: [
  new TextRun({ text: "Proyecto Integrador — Riesgo de bajo desempeño en Saber Pro — página ", font: FONT, size: 15 }),
  new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 15 })] })] });
const doc = new Document({
  creator: "Equipo del proyecto integrador", title: "Predicción del riesgo de bajo desempeño en Saber Pro",
  styles: { default: { document: { run: { font: FONT, size: 18 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 18 }, paragraph: { spacing: { before: 140, after: 70 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 18, italics: true }, paragraph: { spacing: { before: 80, after: 40 }, keepNext: true, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 300, hanging: 200 } } } }] }] },
  sections: [
    { properties: { page }, footers: { default: footer }, children: build(head) },
    { properties: { page, type: SectionType.CONTINUOUS, column: { count: 2, space: 360 } }, footers: { default: footer }, children: build(rest) }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync("reports/Informe_Avance_Riesgo_Saber_Pro.docx", b); console.log("ok", b.length); });
