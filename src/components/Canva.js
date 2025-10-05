class PaletteImage {
    constructor(palette) {
        // 固定Math.random的种子为114514
        this.palette = palette.map(row => [...row]);    // copy
        this.height = this.palette.length;
        this.width = this.palette[0].length;
        this.colorMap = this.getColorMap();
        this.hoverElement = null;
        this.hoverColor = {
            r: 212,
            g: 240,
            b: 248
        }
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

        this.numSegs = maxIndex;

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
                    rgbData[pixelIndex + 3] = 128;               // A (半透明)
                } else {
                    // 索引为0的像素保持透明
                    rgbData[pixelIndex] = 0;
                    rgbData[pixelIndex + 1] = 0;
                    rgbData[pixelIndex + 2] = 0;
                    rgbData[pixelIndex + 3] = 0;
                }
            }
        }

        return rgbData;
    }

    delete(ctx, layer, x, y) {
        console.log('deletion activated at ', y, x);
        // 检查坐标是否有效
        if (y < 0 || y >= this.height || x < 0 || x >= this.width) {
            return;
        }

        // 获取该位置的索引值
        const index = this.palette[y][x];   // NOTE: 因为屏幕坐标和标准图片坐标是反过来的

        // 如果索引为0，直接返回
        if (index === 0) {
            console.log('deletion at empty position. skipped.')
            return;
        }

        // 找到所有具有相同索引值的像素并高亮显示
        const height = this.palette.length;
        const width = this.palette[0].length;

        var imageData = ctx.getImageData(0, 0, this.width, this.height);

        console.time('delete-operation');
        for (let i = 0; i < height; i++) {
            const row = this.palette[i];
            for (let j = 0; j < width; j++) {
                if (row[j] === index) {
                    row[j] = 0;
                    const pixelIndex = (i * width + j) * 4;
                    // 设置为透明 (0, 0, 0, 0)
                    imageData.data[pixelIndex + 3] = 0; // 仅改 Alpha 通道即可
                }
            }
        }
        console.timeEnd('delete-operation');

        console.time('rerender-image-data');
        ctx.putImageData(imageData, 0, 0);
        layer.value.getNode().batchDraw();
        console.timeEnd('rerender-image-data');
    }

    update(ctx, layer, mask, invasive = false) {
        console.log('update activated for ', this.numSegs);

        this.numSegs = this.numSegs + 1     // NOTE: not actually the number of segments, because some are deleted.
        const r = Math.floor(Math.random() * 256);
        const g = Math.floor(Math.random() * 256);
        const b = Math.floor(Math.random() * 256);
        this.colorMap[this.numSegs] = { r: r, g: g, b: b };

        var imageData = ctx.getImageData(0, 0, this.width, this.height);
        for (let i = 0; i < this.height; i++) {
            for (let j = 0; j < this.width; j++) {
                if (mask[i][j] != 0) {
                    if (invasive || this.palette[i][j] == 0) {
                        this.palette[i][j] = this.numSegs;
                        const pixelIndex = (i * this.width + j) * 4;
                        imageData.data[pixelIndex] = r;     // R
                        imageData.data[pixelIndex + 1] = g; // G
                        imageData.data[pixelIndex + 2] = b; // B
                        imageData.data[pixelIndex + 3] = 128; // A
                    }
                }
            }
        }

        ctx.putImageData(imageData, 0, 0);
        layer.value.getNode().batchDraw();
    }

    dehighlight(ctx, layer, index, render = true) {
        var imageData = ctx.getImageData(0, 0, this.width, this.height);
        for (let i = 0; i < this.height; i++) {
            const row = this.palette[i];
            for (let j = 0; j < this.width; j++) {
                if (row[j] == index) {
                    const pixelIndex = (i * this.width + j) * 4;
                    imageData.data[pixelIndex] = this.colorMap[index].r;     // R
                    imageData.data[pixelIndex + 1] = this.colorMap[index].g; // G
                    imageData.data[pixelIndex + 2] = this.colorMap[index].b; // B
                    imageData.data[pixelIndex + 3] = 64; // A
                }
            }
        }
        if (render) {
            ctx.putImageData(imageData, 0, 0);
            layer.value.getNode().batchDraw();
        }
    }

    highlight(ctx, layer, index, render = true) {
        var imageData = ctx.getImageData(0, 0, this.width, this.height);
        for (let i = 0; i < this.height; i++) {
            const row = this.palette[i];
            for (let j = 0; j < this.width; j++) {
                if (row[j] == index) {
                    const pixelIndex = (i * this.width + j) * 4;
                    imageData.data[pixelIndex] = this.hoverColor.r;     // R
                    imageData.data[pixelIndex + 1] = this.hoverColor.g; // G
                    imageData.data[pixelIndex + 2] = this.hoverColor.b; // B
                    imageData.data[pixelIndex + 3] = 64; // A
                }
            }
        }
        if (render) {
            ctx.putImageData(imageData, 0, 0);
            layer.value.getNode().batchDraw();
        }
    }

    hover(ctx, layer, x, y) {

        // restore the color of the previous hover region
        const hoverIndex = this.hoverElement;
        if (hoverIndex) {
            this.dehighlight(ctx, layer, hoverIndex, render = false);
        }

        // highlight hover region        
        // 检查坐标是否有效
        if (y < 0 || y >= this.height || x < 0 || x >= this.width) {
            this.hoverElement = null;
            return;
        }

        // 获取该位置的索引值
        const index = this.palette[y][x];   // NOTE: 因为屏幕坐标和标准图片坐标是反过来的
        if (index == this.hoverElement || index == 0) {
            return;
        }

        this.hoverElement = index;
        this.highlight(ctx, layer, index);
    }

    fullRender(ctx, layer) {
        const rgbData = this.createRGBFromPalette();
        var imageData = ctx.createImageData(this.width, this.height);
        for (let i = 0; i < this.height; i++) {
            for (let j = 0; j < this.width; j++) {
                const pixelIndex = (i * this.width + j) * 4;
                imageData.data[pixelIndex + 0] = rgbData[pixelIndex + 0];
                imageData.data[pixelIndex + 1] = rgbData[pixelIndex + 1];
                imageData.data[pixelIndex + 2] = rgbData[pixelIndex + 2];
                imageData.data[pixelIndex + 3] = rgbData[pixelIndex + 3];
            }
        }
        ctx.putImageData(imageData, 0, 0);
        layer.value.getNode().batchDraw();
    }
}

// 导出函数和类以便在其他地方使用
export { PaletteImage };
