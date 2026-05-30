# Jetson Orin NX（Ubuntu 22.04）安装 RealSense D435i 完整步骤
Jetson 平台**不装 DKMS 内核模块**，用 **RSUSB 后端 + CUDA 加速** 源码编译最稳，全程不修改内核、不冲突 JetPack。

---
## 一、准备工作
- 系统：Ubuntu 22.04（JetPack 6.x）
- 相机：D435i
- 连接：**必须 USB 3.0 线 + USB 3.0 口**
- 先更新系统
```bash
sudo apt update && sudo apt upgrade -y
```

---
## 二、安装依赖
```bash
sudo apt install -y \
git cmake build-essential \
libusb-1.0-0-dev libssl-dev pkg-config \
libgtk-3-dev libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev
```

---
## 三、克隆源码（新仓库地址）
```bash
git clone https://github.com/realsenseai/librealsense.git
cd librealsense
```
可选：切稳定版（推荐）
```bash
git checkout v2.56.5
```

---
## 四、配置 UDEV 规则（必做）
```bash
sudo cp config/99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

---
## 五、编译安装（核心参数）
```bash
mkdir build && cd build

cmake .. \
-DFORCE_RSUSB_BACKEND=ON \
-DBUILD_WITH_CUDA=ON \
-DBUILD_EXAMPLES=ON \
-DBUILD_GRAPHICAL_EXAMPLES=ON \
-DCMAKE_BUILD_TYPE=Release

make -j$(nproc)
sudo make install
sudo ldconfig
```
### 关键参数说明
- `FORCE_RSUSB_BACKEND=ON`：纯用户态 USB 后端，**不依赖内核补丁**，Jetson 必开
- `BUILD_WITH_CUDA=ON`：启用 Orin NX GPU 加速
- 不使用 `librealsense2-dkms`，Jetson 不支持

---
## 六、验证安装
1. 插上 D435i（USB 3.0）
2. 启动查看器
```bash
realsense-viewer
```
看到 **RGB + Depth + IMU** 三数据流正常即成功。

---
## 七、Python 绑定（可选）
```bash
cd build
cmake .. -DBUILD_PYTHON_BINDINGS=ON
make -j$(nproc)
sudo make install
```
测试：
```python
import pyrealsense2 as rs
pipeline = rs.pipeline()
pipeline.start()
frames = pipeline.wait_for_frames()
depth = frames.get_depth_frame()
print(depth.get_width(), depth.get_height())
pipeline.stop()
```

---
## 八、常见问题
1. 找不到设备
   - 换 USB 3.0 线/口
   - 重新执行 UDEV 规则
2. 编译失败
   - 依赖装全
   - 清理 `build` 重新 cmake
3. CUDA 报错
   - 确认 JetPack CUDA 已安装

---
## 九、极简一键脚本（可直接复制运行）
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git cmake build-essential libusb-1.0-0-dev libssl-dev pkg-config libgtk-3-dev libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev
git clone https://github.com/realsenseai/librealsense.git
cd librealsense && git checkout v2.56.5
sudo cp config/99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
mkdir build && cd build
cmake .. -DFORCE_RSUSB_BACKEND=ON -DBUILD_WITH_CUDA=ON -DBUILD_EXAMPLES=ON -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install && sudo ldconfig
realsense-viewer
```

需要我把**ROS 2 Humble 对接 D435i**的启动命令与 launch 文件也给你吗？