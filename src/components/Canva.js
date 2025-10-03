const createRGBFromPalette = (palette) => {
    if (!palette || palette.length === 0) return null;

    const height = palette.length;
    const width = palette[0].length;

    // 创建RGB数组
    const rgbData = new Uint8ClampedArray(height * width * 4);

    // 生成颜色映射表
    const colorMap = {};

    // 找到最大索引值
    let maxIndex = 0;
    for (let i = 0; i < height; i++) {
        for (let j = 0; j < width; j++) {
            if (palette[i][j] > maxIndex) maxIndex = palette[i][j];
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

    // 填充RGB数据
    for (let i = 0; i < height; i++) {
        for (let j = 0; j < width; j++) {
            const index = palette[i][j];
            const pixelIndex = (i * width + j) * 4;

            if (index !== 0 && colorMap[index]) {
                rgbData[pixelIndex] = colorMap[index].r;     // R
                rgbData[pixelIndex + 1] = colorMap[index].g; // G
                rgbData[pixelIndex + 2] = colorMap[index].b; // B
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
};

const ImgToBase64 = async (rgbData) => {
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
};

// 导出函数以便在其他地方使用
export { createRGBFromPalette, ImgToBase64 };
