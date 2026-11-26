typedef unsigned int u32;
static int sys3(int n,int a,int b,int c){
    register int r7 __asm__("r7")=n, r0 __asm__("r0")=a, r1 __asm__("r1")=b, r2 __asm__("r2")=c;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r7),"r"(r1),"r"(r2) : "memory"); return r0;
}
struct event {u32 sec,usec; unsigned short type,code; int value;};
static int number(const char *s){int n=0; if(!*s)return -1; for(;*s;s++){if(*s<'0'||*s>'9'||n>10000)return -1;n=n*10+*s-'0';}return n;}
__attribute__((used)) static int run(int *stk){
    int n=stk[0]; int touch=sys3(5,(int)"/dev/input/event0",n==3?1:0,0);
    if(touch<0)return 1;
    if(n==1){int a[6],b[6],fb[40]; int f=sys3(5,(int)"/dev/fb0",0,0);
        if(f<0||sys3(54,f,0x4600,(int)fb)<0||sys3(54,touch,0x80184540,(int)a)<0||sys3(54,touch,0x80184541,(int)b)<0)return 2;
        return sys3(4,1,(int)a,24)==24&&sys3(4,1,(int)b,24)==24&&sys3(4,1,(int)fb,24)==24?0:3;
    }
    if(n!=3)return 4;
    int x=number((char*)stk[2]),y=number((char*)stk[3]);if(x<0||x>4095||y<0||y>4095)return 5;
    struct event down[]={ {0,0,3,0,x},{0,0,3,1,y},{0,0,1,330,1},{0,0,0,0,0} };
    struct event move[]={ {0,0,3,0,x},{0,0,3,1,y},{0,0,0,0,0} };
    struct event up[]={ {0,0,1,330,0},{0,0,0,0,0} }; int wait[2]={0,18000000};
    if(sys3(4,touch,(int)down,sizeof down)!=sizeof down)return 6;
    for(int i=0;i<9;i++){
        sys3(162,(int)wait,0,0);
        move[0].value=x+(i&1); move[1].value=y+(i&1);
        if(sys3(4,touch,(int)move,sizeof move)!=sizeof move)return 8;
    }
    return sys3(4,touch,(int)up,sizeof up)==sizeof up?0:7;
}
__attribute__((naked)) void _start(void){__asm__ volatile("mov r0, sp\n bl run\n mov r7, #1\n svc #0");}
