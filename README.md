
# fakeleaf-bridge

## 📌 Overview

`fakeleaf-bridge` is a Python backend for `fakeleaf.nvim`.

It is responsible for:

* Connecting to Overleaf via WebSocket
* Handling document synchronization
* Implementing Operational Transform (OT)
* Managing communication with Neovim via stdin/stdout

This project acts as the **backend layer** of the fakeleaf system.

---

## 🧠 Architecture

```
Neovim (fakeleaf.nvim)
        ↓
Python (fakeleaf-bridge)
        ↓
Overleaf WebSocket
```

Communication with Neovim is done via a JSON-based protocol over stdin/stdout.

---

## 🚧 Current Status

⚠️ **Experimental and under heavy development**

* Protocol is not stable
* OT implementation is incomplete
* Many parts are still being tested

---

## 🧪 Development Disclaimer

This project currently includes:

* Experimental WebSocket handling
* Incomplete OT logic
* Debugging utilities

👉 It is **not production-ready**.

---

## ⚖️ Disclaimer

* This project is **not affiliated with Overleaf**
* It is intended for **educational and research purposes**
* No guarantee of compatibility or correctness

If the Overleaf team has any concerns, they are welcome to **contact me personally**, and I will address the situation.

---

## 📦 Installation

### From source (development)

```bash
pip install -e .
```

### Planned

```bash
pip install fakeleaf-bridge
```

---

## ▶️ Usage

Once installed:

```bash
fakeleaf-bridge
```

This starts the backend process, which communicates with Neovim.

---

## 🔗 Related Project

Frontend:

* https://github.com/yourname/fakeleaf.nvim

---

## 🔮 Future Plans

* Stable OT implementation
* Robust WebSocket handling
* Defined message protocol
* Improved error handling
* Packaging and release on PyPI

---

## 🤝 Contributions

Contributions are welcome, but expect breaking changes.

---

## 📄 License

MIT License
