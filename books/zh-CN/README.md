# 简体中文网页版

简体中文版基于 Duc-Tam Nguyen 的 [The Little Book of C](https://github.com/little-book-of/c)
v0.5.0，先用机器翻译，再对照原文校订术语和表述。示例代码、章节锚点和原作署名随网页保留。
译文与原作均采用 [CC BY-NC-SA 4.0](../../LICENSE)。

[中文首页](https://codeideaai.github.io/c/) · [English](https://codeideaai.github.io/c/en/)。
原中文首页 `/c/zh/` 和中英文正文链接仍可直接访问。

## 术语约定

| 英文 | 简体中文 |
| --- | --- |
| scope / lifetime / linkage | 作用域 / 生存期 / 链接属性 |
| structure / union / bit-field | 结构体 / 联合体 / 位域 |
| stack / heap | 栈 / 堆 |
| pointer arithmetic / dereference | 指针运算 / 解引用 |
| undefined behavior / implementation-defined behavior | 未定义行为 / 实现定义的行为 |
| data race / race condition / memory order | 数据竞争 / 竞态条件 / 内存序 |
| header file / header guard | 头文件 / 包含保护 |
| endianness / little-endian / big-endian | 字节序 / 小端 / 大端 |

类型名、函数名、宏和命令保留原文拼写。有关内存分配、类型限定符和原子操作的
说明可对照 [WG14 的 C 标准草案](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf)。

## 维护译文

`translations.json` 保存英文段落与简体中文译文。段落中的 `⟦0⟧` 等标记
代表内联 HTML 标签、代码或其他不可翻译内容。修订译文时应保留这些标记。
修改译文后，在仓库根目录运行以下命令更新 GitHub Pages 文件。

```sh
python3 -m pip install lxml
python3 tools/build_chinese_site.py
```

生成器以 Quarto 渲染的英文 HTML 为输入。如果重新渲染英文，用同一命令
恢复默认中文首页、独立英文首页和语言切换链接。英文原文变更后，需要先为
新增或修改的段落补充译文。PDF、EPUB 和 LaTeX 下载使用原作的英文版本。
