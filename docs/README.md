# How to compile

```bash
cd docs
sphinx-apidoc -o ./source ../demeter
# then add _typing to .rst files, and modify titles etc.
make clean && make html
```