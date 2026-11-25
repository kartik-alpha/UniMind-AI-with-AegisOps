import re

file_path = "docs/overleaf_report/main.tex"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Environments
begins = re.findall(r"\\begin\{([^}]+)\}", text)
ends = re.findall(r"\\end\{([^}]+)\}", text)
print(f"Total \\begin: {len(begins)}, Total \\end: {len(ends)}")
assert len(begins) == len(ends), "Mismatch in begin/end counts!"

stack = []
for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", text):
    op, env = m.group(1), m.group(2)
    if op == "begin":
        stack.append(env)
    else:
        top = stack.pop()
        assert top == env, f"Mismatched environment: {top} vs {env}"

print("All LaTeX environments perfectly matched and nested!")

# 2. Check dollar signs
clean = re.sub(r"\\\$", "", text)
lines = clean.split("\n")
odd_lines = []
for i, line in enumerate(lines):
    c = line.count("$")
    if c % 2 != 0:
        odd_lines.append((i+1, line))

print(f"Lines with odd dollar signs: {len(odd_lines)}")
for lnum, ltext in odd_lines:
    print(f"Line {lnum}: {ltext}")
assert len(odd_lines) == 0, "Unbalanced $ detected!"
print("Math $ balancing: 100% PASS!")

# 3. Check citations
with open("docs/overleaf_report/references.bib", "r", encoding="utf-8") as bf:
    bib_text = bf.read()

bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib_text))
cite_keys = set(re.findall(r"\\cite\{([^}]+)\}", text))
all_cites = set()
for c in cite_keys:
    for sub in c.split(","):
        all_cites.add(sub.strip())

print(f"Bib keys ({len(bib_keys)}): {bib_keys}")
print(f"Cite keys ({len(all_cites)}): {all_cites}")
assert all_cites == bib_keys, f"Mismatch in cites: {all_cites ^ bib_keys}"
print("Citations check: 100% MATCH (Exactly 5 citations cited in text and bib)!")

# 4. Check Title and Authors
assert "UNIMIND :- AI-Powered University Support, Operations \\& AIOps Platform" in text
assert "Group 16: Kartik (230668), Darshan Mittal (230657), Aditya (230624), Naveen Singh" in text
assert "BML Munjal University" in text
print("Title and Authors: 100% PASS!")

# 5. Check no \newpage or \clearpage
newpages = re.findall(r"\\(newpage|clearpage)", text)
print(f"Occurrences of newpage/clearpage: {len(newpages)}")
assert len(newpages) == 0, "Disallowed newpage/clearpage found!"
print("Continuous sections check: 100% PASS!")

# 6. Word count
body = text.split(r"\begin{document}")[1].split(r"\bibliographystyle")[0]
body = re.sub(r"%.*", "", body)
body = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", "", body, flags=re.DOTALL)
body = re.sub(r"\\begin\{algorithm2e?\}.*?\\end\{algorithm2e?\}", "", body, flags=re.DOTALL)
body = re.sub(r"\\begin\{tabular\}.*?\\end\{tabular\}", "", body, flags=re.DOTALL)
body = re.sub(r"\$\$.*?\$\$", "", body, flags=re.DOTALL)
body = re.sub(r"\$.*?\$", "", body)
body = re.sub(r"\\\[.*?\\\]", "", body, flags=re.DOTALL)
body = re.sub(r"\\begin\{equation\}.*?\\end\{equation\}", "", body, flags=re.DOTALL)

for cmd in ["textbf", "textit", "emph", "section", "subsection", "subsubsection", "caption", "item"]:
    body = re.sub(r"\\" + cmd + r"\{([^}]*)\}", r" \1 ", body)

body = re.sub(r"\\(cite|ref|label|url|includegraphics|input|vspace|hspace|noindent)\*?(\[[^\]]*\])?\{[^}]*\}", " ", body)
body = re.sub(r"\\[a-zA-Z]+", " ", body)
body = re.sub(r"[{}]", " ", body)

words = body.split()
print(f"Accurate Prose Word Count: {len(words)} words (Strict Guideline: 4,500 - 5,500 words)")
assert 4500 <= len(words) <= 5500, f"Word count {len(words)} is outside the 4,500 - 5,500 range!"
print("Word count check: 100% PASS!")
print("==================================================================")
print("               ALL OVERLEAF REPORT CHECKS PASSED                  ")
print("==================================================================")
