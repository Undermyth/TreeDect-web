class IndexObject {
    constructor(index, x, y) {
        this.index = index;
        this.x = x;
        this.y = y;
    }
}

function updateIndexArray(indexArray, labels, position_x, position_y) {
    for (let i = 0; i < labels.length; i++) {
        indexArray[i] = new IndexObject(labels[i], position_x[i], position_y[i]);
    }
}

export { IndexObject, updateIndexArray };