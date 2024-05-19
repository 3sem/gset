#include <stdio.h>

int m() {
 int t = 5;
	return t;
}

int n(float k, float m) {
    while (k > 0)
        {
        k-= 1 / m*k;
        if (k * m > 0.00001) {
                printf("tr1 %f", (int)m%(int)k);
                return (int)(k);
            }
        }
        printf("tr2 %f", k);
        return m*k;
}
