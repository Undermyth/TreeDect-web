class PaletteImage {
    constructor(palette) {
        // 固定Math.random的种子为114514
        Math.random = (function () {
            let seed = 114514;
            return function () {
                seed = (seed * 9301 + 49297) % 233280;
                return seed / 233280;
            };
        })();
        this.palette = palette;
        this.height = this.palette.length;
        this.width = this.palette[0].length;
        this.colorMap = this.getColorMap();
        this.numSegs = Object.keys(this.colorMap).length;
        const rgbResult = this.createRGBFromPalette(); // 修改调用
        this.rgbData = rgbResult;
        this.base64 = null;

        // 异步初始化base64数据
        this.initBase64();
    }

    getColorMap() {
        // 生成颜色映射表
        const colorMap = {};

        // 找到最大索引值
        let maxIndex = 0;
        for (let i = 0; i < this.height; i++) {
            for (let j = 0; j < this.width; j++) {
                if (this.palette[i][j] > maxIndex) maxIndex = this.palette[i][j];
            }
        }

        // 为每个索引生成随机颜色
        for (let i = 1; i <= maxIndex; i++) {
            colorMap[i] = {
                r: Math.floor(Math.random() * 256),
                g: Math.floor(Math.random() * 128),
                b: Math.floor(Math.random() * 256)
            };
        }
        return colorMap;
    }

    // 将createRGBFromPalette转换为类方法
    createRGBFromPalette() {
        if (!this.palette || this.palette.length === 0) return null;

        const height = this.palette.length;
        const width = this.palette[0].length;

        // 创建RGB数组
        const rgbData = new Uint8ClampedArray(height * width * 4);

        // 填充RGB数据
        for (let i = 0; i < height; i++) {
            for (let j = 0; j < width; j++) {
                const index = this.palette[i][j];
                const pixelIndex = (i * width + j) * 4;

                if (index !== 0 && this.colorMap[index]) {
                    rgbData[pixelIndex] = this.colorMap[index].r;     // R
                    rgbData[pixelIndex + 1] = this.colorMap[index].g; // G
                    rgbData[pixelIndex + 2] = this.colorMap[index].b; // B
                    rgbData[pixelIndex + 3] = 255;               // A (半透明)
                } else {
                    // 索引为0的像素保持透明
                    rgbData[pixelIndex] = 0;
                    rgbData[pixelIndex + 1] = 0;
                    rgbData[pixelIndex + 2] = 0;
                    rgbData[pixelIndex + 3] = 0;
                }
            }
        }

        return { data: rgbData, width, height };
    }

    async initBase64() {
        this.base64 = await this.ImgToBase64(this.rgbData); // 修改调用
    }

    // 将ImgToBase64转换为类方法
    async ImgToBase64(rgbData) {
        if (!rgbData) return null;

        // 创建PNG文件头信息
        const pngSignature = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]);

        // 由于直接生成PNG格式比较复杂，我们使用另一种方式：
        // 1. 创建ImageData对象
        // 2. 使用canvas的toBlob方法转换为base64（但不操作DOM）

        // 创建一个临时的OffscreenCanvas（如果支持）
        if (typeof OffscreenCanvas !== 'undefined') {
            const canvas = new OffscreenCanvas(rgbData.width, rgbData.height);
            const ctx = canvas.getContext('2d');
            const imageData = new ImageData(rgbData.data, rgbData.width, rgbData.height);
            ctx.putImageData(imageData, 0, 0);

            // 返回Promise，因为toBlob是异步的
            return canvas.convertToBlob({ type: 'image/png' }).then(blob => {
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            });
        } else {
            // 如果不支持OffscreenCanvas，回退到创建临时canvas的方式
            // 创建一个临时canvas元素
            const canvas = document.createElement('canvas');
            canvas.width = rgbData.width;
            canvas.height = rgbData.height;

            const ctx = canvas.getContext('2d');
            const imageData = new ImageData(rgbData.data, rgbData.width, rgbData.height);
            ctx.putImageData(imageData, 0, 0);

            // 转换为base64
            const dataURL = canvas.toDataURL('image/png');
            // 清理临时元素
            canvas.remove();

            return Promise.resolve(dataURL);
        }
    }

    // 获取base64数据的方法，确保数据已加载
    async getBase64() {
        if (this.base64) {
            return this.base64;
        }
        await this.initBase64();
        return this.base64;
    }

    // 高亮显示与指定坐标相同索引值的所有像素
    async delete(x, y) {
        console.log('deletion activated at ', x, y);
        // 检查坐标是否有效
        if (y < 0 || y >= this.palette.length || x < 0 || x >= this.palette[0].length) {
            return;
        }

        // 获取该位置的索引值
        const index = this.palette[y][x];

        // 如果索引为0，直接返回
        if (index === 0) {
            return;
        }

        // 找到所有具有相同索引值的像素并高亮显示
        const height = this.palette.length;
        const width = this.palette[0].length;

        for (let i = 0; i < height; i++) {
            for (let j = 0; j < width; j++) {
                if (this.palette[i][j] === index) {
                    this.palette[i][j] = 0;
                    const pixelIndex = (i * width + j) * 4;
                    // 设置为浅白色 (255, 255, 255, 200)
                    this.rgbData.data[pixelIndex] = 0;     // R
                    this.rgbData.data[pixelIndex + 1] = 0; // G
                    this.rgbData.data[pixelIndex + 2] = 0; // B
                    this.rgbData.data[pixelIndex + 3] = 0; // A
                }
            }
        }

        // 更新base64值
        this.base64 = await this.ImgToBase64(this.rgbData); // 修改调用
    }

    async update(mask, invasive = false) {
        console.log('update activated for ', this.numSegs);
        this.numSegs = this.numSegs + 1     // NOTE: not actually the number of segments, because some are deleted.
        const r = Math.floor(Math.random() * 256);
        const g = Math.floor(Math.random() * 256);
        const b = Math.floor(Math.random() * 256);
        this.colorMap[this.numSegs] = { r: r, g: g, b: b };
        for (let i = 0; i < this.height; i++) {
            for (let j = 0; j < this.width; j++) {
                if (mask[i][j] != 0) {
                    if (invasive || this.palette[i][j] == 0) {
                        this.palette[i][j] = this.numSegs;
                        const pixelIndex = (i * this.width + j) * 4;
                        this.rgbData.data[pixelIndex] = r;     // R
                        this.rgbData.data[pixelIndex + 1] = g; // G
                        this.rgbData.data[pixelIndex + 2] = b; // B
                        this.rgbData.data[pixelIndex + 3] = 255; // A
                    }
                }
            }
        }
        this.base64 = await this.ImgToBase64(this.rgbData); // 修改调用
    }
}

// 导出函数和类以便在其他地方使用
export { PaletteImage };
