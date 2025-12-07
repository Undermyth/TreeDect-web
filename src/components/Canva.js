class PaletteImage {
    constructor(palette) {
        // 固定Math.random的种子为114514
        this.palette = palette.map(row => [...row]);    // copy
        this.height = this.palette.length;
        this.width = this.palette[0].length;
        this.colorMap = this.getColorMap();
        this.clusterMap = null;     // after clustering, the colormap should be re-indexed by cluster id
        this.hoverElement = [];
        this.hoverColor = {
            r: 255,
            g: 165,
            b: 0
        };
        this.segMap = {};
        this.reverseMap = this.getReverseMap();
        this.modifiedSegments = new Set(); // 存储手动修改过的分割区域
        this.commonAlpha = 160;
    }

    // get reverse indexing for accelerated highlighting. used in constructor and maintained during modification
    getReverseMap() {
        const reverseMap = [];
        for (let i = 0; i < this.height; i++) {
            for (let j = 0; j < this.width; j++) {
                const index = this.palette[i][j];
                if (index !== 0) {
                    if (!reverseMap[index]) {
                        reverseMap[index] = {"data": [], "deleted": []};
                    }
                    reverseMap[index].data.push(i * this.width + j);
                    reverseMap[index].deleted.push(false);
                }
            }
        }
        return reverseMap;
    }

    // create random color mapping. used in constructor
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
                g: Math.floor(Math.random() * 100),
                b: Math.floor(Math.random() * 256)
            };
        }
        return colorMap;
    }

    // util function to convert color map to hex color map for html rendering
    getHexColor() {
        const hexColorMap = {};
        for (let i = 1; i <= this.numSegs; i++) {
            const color = this.colorMap[i];
            const r = color.r.toString(16).padStart(2, '0');
            const g = color.g.toString(16).padStart(2, '0');
            const b = color.b.toString(16).padStart(2, '0');
            hexColorMap[i] = `#${r}${g}${b}`;
        }
        return hexColorMap;
    }

    // create RGB array from palette and colormap. used in rendering
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
                    rgbData[pixelIndex + 3] = this.commonAlpha;               // A (半透明)

                    // if (!(index in this.segMap)) {
                    //     this.segMap[index] = { x: [], y: [] };
                    // }
                    // this.segMap[index].x.push(i);
                    // this.segMap[index].y.push(j);
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

    getIndex(x, y) {
        return this.palette[y][x];
    }

    // delete a segment at cursor position (x, y), and rerender. also maintains reverse map
    delete(ctx, layer, x, y) {
        console.log('deletion activated at ', y, x);
        // 检查坐标是否有效
        if (y < 0 || y >= this.height || x < 0 || x >= this.width) {
            return;
        }

        // 获取该位置的索引值
        const index = this.palette[y][x];   // NOTE: 因为屏幕坐标和标准图片坐标是反过来的
        this.reverseMap[index] = { data: [], deleted: [] };

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

    // add a new segment according to mask, and rerender. also maintains reverse map
    update(ctx, layer, mask, invasive = false) {
        console.log('update activated for ', this.numSegs);

        this.numSegs = this.numSegs + 1     // NOTE: not actually the number of segments, because some are deleted.
        const r = Math.floor(Math.random() * 256);
        const g = Math.floor(Math.random() * 256);
        const b = Math.floor(Math.random() * 256);
        this.colorMap[this.numSegs] = { r: r, g: g, b: b };
        this.reverseMap[this.numSegs] = { data: [], deleted: [] };

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
                        imageData.data[pixelIndex + 3] = this.commonAlpha; // A
                        this.reverseMap[this.numSegs].data.push(i * this.width + j);
                    }
                }
            }
        }

        ctx.putImageData(imageData, 0, 0);
        layer.value.getNode().batchDraw();
    }

    // clear lazy deleted manual modifications
    resortModifiedSegments() {
        for (const index of this.modifiedSegments) {
            const data = this.reverseMap[index].data;
            const deleted = this.reverseMap[index].deleted;
            for (let i = data.length - 1; i >= 0; i--) {
                if (deleted[i]) {
                    data.splice(i, 1);
                    deleted.splice(i, 1);
                }
            }
        }
        this.modifiedSegments.clear();
    }

    // restore the color of the previous highlight region
    dehighlight(ctx, layer, indexes, render = true) {
        var imageData = ctx.getImageData(0, 0, this.width, this.height);
        for (const index of indexes) {
            const clusterIndex = this.clusterMap[index - 1] + 1;
            for (const combinedIndex of this.reverseMap[index].data) {
                const pixelIndex = combinedIndex * 4;
                imageData.data[pixelIndex] = this.colorMap[clusterIndex].r;     // R
                imageData.data[pixelIndex + 1] = this.colorMap[clusterIndex].g; // G
                imageData.data[pixelIndex + 2] = this.colorMap[clusterIndex].b; // B
                imageData.data[pixelIndex + 3] = this.commonAlpha; // A
            }
        }
        if (render) {
            ctx.putImageData(imageData, 0, 0);
            layer.value.getNode().batchDraw();
        }
    }

    // highlight the segment at indexes
    highlight(ctx, layer, indexes, render = true) {
        // console.log('highlighting indexes', indexes);
        var imageData = ctx.getImageData(0, 0, this.width, this.height);
        for (const index of indexes) {
            for (const combinedIndex of this.reverseMap[index].data) {
                const pixelIndex = combinedIndex * 4;
                imageData.data[pixelIndex] = this.hoverColor.r;     // R
                imageData.data[pixelIndex + 1] = this.hoverColor.g; // G
                imageData.data[pixelIndex + 2] = this.hoverColor.b; // B
                imageData.data[pixelIndex + 3] = 200; // A
            }
        }
        if (render) {
            ctx.putImageData(imageData, 0, 0);
            layer.value.getNode().batchDraw();
        }
    }

    // highlight the segment at indexes, and dehighlight the previous highlight region
    uniqueLight(ctx, layer, indexes) {

        // restore the color of the previous hover region
        const hoverIndex = this.hoverElement;
        if (hoverIndex.length > 0) {
            this.dehighlight(ctx, layer, hoverIndex);
        }

        this.hoverElement = indexes;
        this.highlight(ctx, layer, indexes);
    }

    // increase or decrease the segment at index by radius. used for interactive modification
    modify(ctx, layer, index, x, y, increment = true, radius = 5, invasive = false) {
        var imageData = ctx.getImageData(0, 0, this.width, this.height);

        const r2 = radius ** 2;
        const iStart = Math.max(0, y - radius);
        const iEnd = Math.min(this.height, y + radius);
        for (let i = iStart; i < iEnd; i++) {
            const tingent = Math.round(Math.sqrt(r2 - (y - i) ** 2));
            const jStart = Math.max(0, x - tingent);
            const jEnd = Math.min(this.width, x + tingent);
            const row = this.palette[i];
            for (let j = jStart; j < jEnd; j++) {
                const pixelIndex = (i * this.width + j) * 4;
                if (row[j] == 0 && increment) {
                    row[j] = index;
                    imageData.data[pixelIndex] = this.colorMap[index].r;     // R
                    imageData.data[pixelIndex + 1] = this.colorMap[index].g; // G
                    imageData.data[pixelIndex + 2] = this.colorMap[index].b; // B
                    imageData.data[pixelIndex + 3] = this.commonAlpha; // A
                    this.reverseMap[index].data.push(i * this.width + j);
                    this.reverseMap[index].deleted.push(false);
                    this.modifiedSegments.add(index);
                }
                else if (row[j] == index && !increment) {
                    row[j] = 0;
                    imageData.data[pixelIndex + 3] = 0; // A
                    const reverseMapIndex = this.reverseMap[index].data.indexOf(i * this.width + j);
                    this.reverseMap[index].deleted[reverseMapIndex] = true;
                }
            }
        }
        ctx.putImageData(imageData, 0, 0);
        layer.value.getNode().batchDraw();
    }

    // reindexing the colors of the segments according to clusterMap, and rerender
    cluster(ctx, layer, clusterMap) {
        this.clusterMap = clusterMap;
        var imageData = ctx.getImageData(0, 0, this.width, this.height);
        for (let i = 0; i < this.height; i++) {
            const row = this.palette[i];
            for (let j = 0; j < this.width; j++) {
                const index = row[j];
                if (index != 0) {
                    const pixelIndex = (i * this.width + j) * 4;
                    // index - 1: index in [1, segs], clusterMap starting from 0
                    // + 1: kmeans index starting from 0, colorMap from 1
                    const clusterIndex = clusterMap[index - 1] + 1;
                    imageData.data[pixelIndex] = this.colorMap[clusterIndex].r;     // R
                    imageData.data[pixelIndex + 1] = this.colorMap[clusterIndex].g; // G
                    imageData.data[pixelIndex + 2] = this.colorMap[clusterIndex].b; // B
                    imageData.data[pixelIndex + 3] = this.commonAlpha; // A
                }
            }
        }
        ctx.putImageData(imageData, 0, 0);
        layer.value.getNode().batchDraw();
    }

    // update cluster index
    updateClusterIndex(ctx, layer, x, y, clusterIndex, highlighted) {
        const index = this.getIndex(x, y);
        this.clusterMap[index - 1] = clusterIndex;
        if (highlighted) {
            this.hoverElement.push(index);
            this.highlight(ctx, layer, [index]);
        }
        else {
            this.dehighlight(ctx, layer, [index]);
        }
    }

    // render the image with the current palette
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
