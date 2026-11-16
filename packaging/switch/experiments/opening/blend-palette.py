"""Opening replay candidate, selected only for the measured two-matrix blend mode."""
def transform(src):
    anchor='''        if (fk.blend) {
            for (int m = 0; m < 4; m++) {'''
    assert src.count(anchor)==1
    return src.replace(anchor,'''        if (fk.blend) {
            const bool two = fk.blend == 1;
            if (two) {
                std::memcpy(c.wvb[0], c.wv, sizeof c.wv);
                std::memcpy(c.wvbn[0], c.wvn, sizeof c.wvn);
            }
            for (int m = two ? 1 : 0; m < (two ? 2 : 4); m++) {''')
