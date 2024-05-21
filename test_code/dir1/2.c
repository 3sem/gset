typedef int customtype1;
typedef double lol;

int inc() {
 int t;
 return t+1;
}

customtype1 n(lol k, float m) {
    while (k > 0)
        {
        k-= 1 / m*k;
        if (k * m > 0.0001) {
                ;
                return (int)(k);
            }
        }
        inc();
        return m*k;
}
