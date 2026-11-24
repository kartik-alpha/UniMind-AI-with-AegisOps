# STAGE H0 — HARDWARE RESOURCE PROFILE & EXECUTION ENVELOPE

**Target Machine:** Windows 11 Home / Pro (x64)  
**Processor:** Intel Core i5-12450H (8 Cores, 12 Threads)  
**System Memory:** 7.71 GB Usable RAM  
**GPU:** NVIDIA GeForce GTX 1650 (4 GB VRAM)  
**Free Disk Space:** 54.35 GB  

---

## 1. Hardware Allocation Envelopes

To prevent host freezing, memory thrashing, or disk exhaustion on this 8 GB machine, the following operating budgets are strictly mandated:

| Subsystem | Max RAM Allocation | Disk Ceiling | Operating Mode |
| :--- | :--- | :--- | :--- |
| **FastAPI Backend Process** | 450 MB | 50 MB | Single worker, Uvicorn |
| **React + Vite Frontend** | 300 MB | 100 MB | Built static bundle or single dev server |
| **Relational Database** | 350 MB | 500 MB | SQLite default / Single lightweight PostgreSQL when active |
| **Vector Database** | 450 MB | 1000 MB | ChromaDB default / Single Qdrant container when active |
| **Cache & Message Broker** | 100 MB | 100 MB | In-memory default / Single Redis container when active |
| **Object Storage** | 150 MB | 1000 MB | Local filesystem default / Single MinIO when active |
| **Target Combined Development Footprint** | $\le 1.8$ GB | $\le 2.7$ GB | **Leaves $\ge 5.9$ GB RAM for Windows OS** |

---

## 2. Docker & Container Management Rules

1. **Named Compose Profiles:** Services are partitioned into individual profiles:
   - `profiles: ["postgres"]`
   - `profiles: ["qdrant"]`
   - `profiles: ["redis"]`
   - `profiles: ["minio"]`
   - `profiles: ["integration"]`
2. **Never Run All Simultaneously:** Starting PostgreSQL, Qdrant, Redis, MinIO, and Kubernetes simultaneously would consume $> 4.5$ GB of RAM, putting the 8 GB host into swap thrashing. Tests must start and stop services sequentially.
3. **Storage Warning Thresholds:**
   - **Current Free Storage:** 54.35 GB.
   - **Yellow Alert ($< 30$ GB free):** Pause optional container image downloads.
   - **Red Alert ($< 20$ GB free):** Immediate halt of all new installations.
4. **Prohibited Prune Commands:** Destructive commands like `docker system prune --all --volumes` or `git clean -fd` are strictly prohibited.

---

## 3. GPU Utilization Guidelines

- NVIDIA GTX 1650 (4 GB VRAM) is detected with Driver 552.27 and CUDA 12.4.
- Infrastructure adapters (PostgreSQL, Qdrant, Redis, MinIO) do not use or require GPU acceleration.
- SentenceTransformers embedding inference runs by default on CPU with minimal footprint ($< 150$ MB RAM). GPU acceleration is treated strictly as an optional performance enhancement.
