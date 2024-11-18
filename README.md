<h1 align="center">- OneBotZX -</h1>

<p align="center">
<img src="https://img.shields.io/github/license/amakerlife/OneBotZX" alt="License" />
<img src="https://img.shields.io/github/last-commit/amakerlife/OneBotZX">
<img src="https://img.shields.io/badge/OneBot-11-black?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHAAAABwCAMAAADxPgR5AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAAxQTFRF////29vbr6+vAAAAk1hCcwAAAAR0Uk5T////AEAqqfQAAAKcSURBVHja7NrbctswDATQXfD//zlpO7FlmwAWIOnOtNaTM5JwDMa8E+PNFz7g3waJ24fviyDPgfhz8fHP39cBcBL9KoJbQUxjA2iYqHL3FAnvzhL4GtVNUcoSZe6eSHizBcK5LL7dBr2AUZlev1ARRHCljzRALIEog6H3U6bCIyqIZdAT0eBuJYaGiJaHSjmkYIZd+qSGWAQnIaz2OArVnX6vrItQvbhZJtVGB5qX9wKqCMkb9W7aexfCO/rwQRBzsDIsYx4AOz0nhAtWu7bqkEQBO0Pr+Ftjt5fFCUEbm0Sbgdu8WSgJ5NgH2iu46R/o1UcBXJsFusWF/QUaz3RwJMEgngfaGGdSxJkE/Yg4lOBryBiMwvAhZrVMUUvwqU7F05b5WLaUIN4M4hRocQQRnEedgsn7TZB3UCpRrIJwQfqvGwsg18EnI2uSVNC8t+0QmMXogvbPg/xk+Mnw/6kW/rraUlvqgmFreAA09xW5t0AFlHrQZ3CsgvZm0FbHNKyBmheBKIF2cCA8A600aHPmFtRB1XvMsJAiza7LpPog0UJwccKdzw8rdf8MyN2ePYF896LC5hTzdZqxb6VNXInaupARLDNBWgI8spq4T0Qb5H4vWfPmHo8OyB1ito+AysNNz0oglj1U955sjUN9d41LnrX2D/u7eRwxyOaOpfyevCWbTgDEoilsOnu7zsKhjRCsnD/QzhdkYLBLXjiK4f3UWmcx2M7PO21CKVTH84638NTplt6JIQH0ZwCNuiWAfvuLhdrcOYPVO9eW3A67l7hZtgaY9GZo9AFc6cryjoeFBIWeU+npnk/nLE0OxCHL1eQsc1IciehjpJv5mqCsjeopaH6r15/MrxNnVhu7tmcslay2gO2Z1QfcfX0JMACG41/u0RrI9QAAAABJRU5ErkJggg==">
</p>
<p align="center">
    <img src="https://socialify.git.ci/amakerlife/OneBotZX?description=1&forks=1&issues=1&language=1&name=1&owner=1&pulls=1&stargazers=1&theme=Light">
</p>



对接 OneBot 标准 HTTP 的 Zhixue 机器人

---

## 快速开始

```bash
git clone https://github.com/amakerlife/OneBotZX
cd OneBotZX
mv config.example.yml config.yml
vim config.yml
pip install -r requirements.txt
python bot.py
```

## Todo List

- [ ] 重构 `send_message`
- [ ] 正向 WebSocket 支持
- [ ] 自定义字体文件路径
- [ ] 各种操作失败提示
- [ ] 管理员查看教师端考试列表
- [ ] 支持为用户分配自定义权限（可能伴随着更改配置文件格式为 json）
- [ ] 支持查看题目答案

## 提示

使用本项目前，请确保拥有目标学校具有查看至少校级报告权限的教师账号。如需全部功能，请添加校长/管理员账号。本项目不会提供验证码 API，请自行解决。
