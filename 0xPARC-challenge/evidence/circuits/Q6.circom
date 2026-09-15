pragma circom 2.2.3;

template Main() {
    signal input r;
    signal input s;

    ((-1)+(1)*r) * ((0)+(1)*s) === (1);
}

component main = Main();
