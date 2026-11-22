# 简体中文网页版

简体中文版基于 Duc-Tam Nguyen 的 [The Little Book of C](https://github.com/little-book-of/c)
v0.5.0，通过机器翻译生成。示例代码、章节锚点和原作署名随网页保留。
译文与原作均采用 [CC BY-NC-SA 4.0](../../LICENSE)。

`translations.json` 保存英文段落与简体中文译文。段落中的 `⟦0⟧` 等标记
代表内联 HTML 标签、代码或其他不可翻译内容。修订译文时应保留这些标记。
修改译文后，在仓库根目录运行以下命令更新 GitHub Pages 文件。

```sh
python3 -m pip install lxml
python3 tools/build_chinese_site.py
```

生成器以 Quarto 渲染的英文 HTML 为输入。如果重新渲染英文，用同一命令
恢复英文页面的语言链接并重新生成 `docs/zh/`。英文原文变更后，需要先为
新增或修改的段落补充译文。PDF、EPUB 和 LaTeX 下载使用原作的英文版本。
