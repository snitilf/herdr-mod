// Read-only changes across repositories directly under the focused folder.
import { View, div, svg } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { spaces, panes, focused, exec, readTextFile, theme, settings, shared, setShared, pickFolder } from "herdr";

const READ = ["--no-optional-locks", "-c", "core.fsmonitor=false", "-c", "diff.autoRefreshIndex=false"];
function location() {
  const space = spaces().find(s => s.active), f = focused();
  const pane = f?.pane ? panes().find(p => p.pane === f.pane) : null;
  const on = f?.pane === null ? (f.terminal?.includes("/") ? f.terminal.split("/")[0] : null) : space?.machine ?? null;
  return { cwd: (!on && shared("iris.panelRoots.v1")?.[f?.tab]) || pane?.cwd || f?.cwd || space?.folder, on };
}
const key = () => JSON.stringify(location());
function chooseFolder(cx) {
  const tab = focused()?.tab;
  if (!tab || location().on) return;
  cx.spawn(async cx => {
    const folder = await pickFolder({ prompt: "Choose a folder for Files and Changes" });
    if (folder) setShared("iris.panelRoots.v1", { ...(shared("iris.panelRoots.v1") ?? {}), [tab]: folder });
    cx.notify();
  });
}
function folderBar(t) {
  const f = focused(), loc = location();
  return h_flex().h(30).px(10).gap(8).items_center().border_b(1).border_color(t.border)
    .child(div().flex_1().min_w(0).truncate().text_size(11).text_color(t.muted).child(loc.cwd || "No folder"))
    .when(!loc.on && Boolean(f?.tab), el => el.child(div().id("choose-folder").px(4).cursor_pointer().text_size(11).text_color(t.accent).on_click((_e,cx) => chooseFolder(cx)).child("Folder")));
}
const label = path => path.split("/").filter(Boolean).pop() || path;

export default class Repositories extends View {
  init(_props, cx) {
    this.repos = []; this.folded = new Set(); this.loading = false; this.context = null; this.selected = null; this.diff = null;
    this.refresh(cx);
    cx.timer.every(15000, cx => this.refresh(cx));
  }
  refresh(cx) {
    const context = key(), { cwd, on } = location();
    if (this.context !== context) { this.context = context; this.repos = []; this.selected = null; this.diff = null; this.error = null; this.folded = new Set(); }
    if (!cwd || this.loading) return;
    this.loading = true;
    cx.spawn(async cx => {
      try {
        // Scan up to three folders deep, excluding dependency trees and hidden folders.
        const script = 'find "$1" -mindepth 1 -maxdepth 4 \\( -name .git \\( -type d -o -type f \\) -print0 -prune \\) -o \\( -type d \\( -name node_modules -o -name vendor -o -name target -o -name .venv -o -name Library -o -name \'.*\' \\) -prune \\) 2>/dev/null; true';
        const own = await exec("git", ["rev-parse", "--show-toplevel"], { cwd, on }).catch(() => null);
        const list = await exec("sh", ["-c", script, "repos", cwd], { on });
        if (list.code !== 0) throw new Error(list.stderr || "Cannot list folders");
        const roots = [...new Set([...(own?.code === 0 ? [own.stdout.trim()] : []), ...list.stdout.split("\0").filter(Boolean).map(path => path.slice(0, -5))])].sort((a,b) => a.localeCompare(b));
        const repos = [];
        for (const root of roots.slice(0, 100)) {
          const r = await exec("git", [...READ, "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=normal"], { cwd: root, on });
          const entries = r.code === 0 ? r.stdout.split("\0").filter(Boolean) : [];
          repos.push({ root, name: label(root), error: r.code === 0 ? null : "Cannot read repository", files: entries.slice(0, 300).map(entry => ({ status: entry.slice(0,2), path: entry.slice(3) })), limited: entries.length > 300 });
        }
        if (key() !== context) return;
        this.repos = repos; this.limited = roots.length > 100; this.error = null;
      } catch (e) { if (key() === context) this.error = String(e); }
      finally { this.loading = false; cx.notify(); }
    });
  }
  open(repo, file, cx) {
    const context = this.context, selected = JSON.stringify([repo.root, file.path]);
    this.selected = selected; this.diff = "Loading diff..."; cx.notify();
    cx.spawn(async cx => {
      try {
        const { on } = location();
        if (file.status === "??") {
          const text = await readTextFile(`${repo.root}/${file.path}`, { on }).catch(() => null);
          if (key() !== context || this.selected !== selected) return;
          this.diff = text === null ? "Cannot preview this file or folder." : text.includes("\0") ? "Binary file - no text preview." : (text.slice(0, 80000) || "Empty file.");
        }
        else {
          const head = await exec("git", [...READ, "rev-parse", "--verify", "HEAD"], { cwd: repo.root, on });
          const r = await exec("git", [...READ, "diff", ...(head.code === 0 ? ["HEAD"] : ["--cached"]), "--no-ext-diff", "--no-textconv", "--no-color", "--", file.path], { cwd: repo.root, on });
          if (key() !== context || this.selected !== selected) return;
          this.diff = r.code === 0 ? (r.stdout.slice(0, 80000) || "No text diff available.") : (r.stderr || "Cannot load diff.");
        }
      } catch (e) { if (key() === context && this.selected === selected) this.diff = String(e); }
      finally { cx.notify(); }
    });
  }
  render(cx) {
    if (key() !== this.context) this.refresh(cx);
    const t = theme();
    const rows = [];
    for (const repo of this.repos) {
      const folded = this.folded.has(repo.root);
      rows.push(h_flex().id(`repo-${repo.root}`).h(32).px(8).gap(8).items_center().rounded(6).hover(s => s.bg(t.hover)).on_click((_e,cx) => { folded ? this.folded.delete(repo.root) : this.folded.add(repo.root); cx.notify(); })
        .child(svg(`mods/workspace-chrome/chevron-${folded ? "right" : "down"}.svg`).size(12).flex_none().text_color(t.muted))
        .child(div().flex_1().min_w(0).truncate().font_semibold().child(repo.name))
        .child(div().text_size(11).text_color(t.muted).child(repo.error ? "error" : `${repo.files.length} changed`)));
      if (!folded) {
        if (!repo.files.length) rows.push(div().pl(30).py(4).text_size(11).text_color(t.muted).child(repo.error || "No changes"));
        for (const f of repo.files) rows.push(h_flex().id(`file-${repo.root}-${f.path}`).h(27).pl(30).pr(8).gap(8).items_center().rounded(6).hover(s => s.bg(t.hover)).when(this.selected === JSON.stringify([repo.root,f.path]), e => e.bg(t.selected)).on_click((_e,cx) => this.open(repo,f,cx))
          .child(div().w(20).flex_none().text_size(10).text_color(f.status === "??" || f.status.includes("A") ? t.ansi2 : f.status.includes("D") || f.status.includes("U") ? t.ansi1 : t.blocked).child(f.status.trim()))
          .child(div().flex_1().min_w(0).truncate().child(f.path)));
        if (repo.limited) rows.push(div().pl(30).text_size(11).text_color(t.muted).child("First 300 files shown"));
      }
    }
    return v_flex().id("iris-repositories").size_full().min_h(0).rounded(10).overflow_hidden().bg(t.background).border_1().border_color(t.border).text_color(t.foreground).font_family(settings().font_family ?? "Paper Mono").text_size(13)
      .child(h_flex().h(42).px(14).gap(8).items_center().border_b(1).border_color(t.border).child(div().font_semibold().child("Changes"))
        .child(div().flex_1()).child(div().text_size(11).text_color(t.muted).child(`${this.repos.length} repositories`))
        .child(div().id("refresh-repos").px(6).cursor_pointer().on_click((_e,cx) => this.refresh(cx)).child("Refresh")))
      .child(folderBar(t))
      .child(v_flex().id("repo-list").flex_1().min_h(0).overflow_y_scrollbar().p(6).children(rows)
        .when(!rows.length, el => el.child(div().p(8).text_color(t.muted).child(this.error || (this.loading ? "Finding repositories..." : "No repositories found in this folder"))))
        .when(Boolean(this.limited), el => el.child(div().p(8).text_size(11).text_color(t.muted).child("First 100 repositories shown"))))
      .when(Boolean(this.diff), el => el.child(v_flex().h(220).border_t(1).border_color(t.border)
        .child(h_flex().h(30).px(10).items_center().child(div().flex_1().text_size(11).text_color(t.muted).child("Diff preview"))
          .child(div().id("close-diff").cursor_pointer().on_click((_e,cx) => { this.diff = null; this.selected = null; cx.notify(); }).child("Close")))
        .child(v_flex().id("diff-preview").flex_1().min_h(0).overflow_y_scrollbar().px(10).text_size(11)
          .children((this.diff ?? "").split("\n").slice(0, 500).map(line => div().text_color(line.startsWith("+") && !line.startsWith("+++") ? t.ansi2 : line.startsWith("-") && !line.startsWith("---") ? t.ansi1 : line.startsWith("@@") || line.startsWith("diff ") || line.startsWith("index ") ? t.muted : t.foreground).child(line || " "))))));
  }
}
