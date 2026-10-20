// Stage-one infrastructure only: independent cubic reference and data generator.
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using Matrix = std::vector<int64_t>;
Matrix multiply(const Matrix& a, const Matrix& b, int n) {
    Matrix c(n*n,0);
    for(int i=0;i<n;++i) for(int t=0;t<n;++t) for(int j=0;j<n;++j)
        c[i*n+j] += a[i*n+t]*b[t*n+j];
    return c;
}
int main(int argc,char** argv) {
    try {
        if(argc<3) throw std::runtime_error("generate output n seed kind mutation | check input");
        std::string mode=argv[1];
        if(mode=="generate") {
            if(argc!=8) throw std::runtime_error("generate output n seed kind mutation low");
            int n=std::stoi(argv[3]), low=std::stoi(argv[7]);
            if(n<1||n>1024||low < -9||low>0) throw std::runtime_error("range error");
            uint64_t seed=std::stoull(argv[4]); std::mt19937_64 rng(seed);
            std::string kind=argv[5], mutation=argv[6];
            Matrix a(n*n),b(n*n);
            // Explicit rejection sampling avoids library-dependent distribution mapping.
            auto draw=[&](){ uint64_t width=uint64_t(10-low),x,threshold=uint64_t(-width)%width;
                do{x=rng();}while(x<threshold); return low+int(x%width); };
            for(auto& x:a)x=draw();
            for(auto& x:b)x=draw();
            if(kind=="zero") std::fill(a.begin(),a.end(),0);
            else if(kind=="identity") { std::fill(a.begin(),a.end(),0); for(int i=0;i<n;++i)a[i*n+i]=1; }
            else if(kind=="diagonal") { std::fill(a.begin(),a.end(),0); std::fill(b.begin(),b.end(),0);
                for(int i=0;i<n;++i){a[i*n+i]=draw();b[i*n+i]=draw();} }
            else if(kind!="random") throw std::runtime_error("unknown kind");
            Matrix c=multiply(a,b,n);
            if(mutation=="single") c[0]+=1;
            else if(mutation=="multi" && n>=2){c[0]+=1;c[n*n-1]+=2;}
            else if(mutation=="cancel" && n>=2){c[0]+=1;c[1]-=1;}
            else if(mutation!="none") throw std::runtime_error("invalid mutation");
            std::ofstream out(argv[2],std::ios::binary); if(!out)throw std::runtime_error("cannot open output");
            out<<n<<'\n'; for(const auto* m:{&a,&b,&c})for(int i=0;i<n;++i){
                for(int j=0;j<n;++j)out<<(*m)[i*n+j]<<(j+1==n?'\n':' '); }
            if(!out)throw std::runtime_error("write failed");
        } else if(mode=="check") {
            if(argc!=3)throw std::runtime_error("check input");
            std::ifstream in(argv[2]); int n;
            if(!(in>>n)||n<1||n>1024)throw std::runtime_error("invalid n");
            Matrix a(n*n),b(n*n),c(n*n);
            for(auto* m:{&a,&b,&c})for(auto& x:*m)if(!(in>>x))throw std::runtime_error("incomplete input");
            std::string extra;if(in>>extra)throw std::runtime_error("extra input");
            for(const auto* m:{&a,&b})for(auto x:*m)if(x < -9||x>9)throw std::runtime_error("AB range");
            for(auto x:c)if(x < -81LL*n-2||x>81LL*n+2)throw std::runtime_error("C range");
            std::cout<<"{\"accepted\":"<<(multiply(a,b,n)==c?"true":"false")<<"}\n";
        } else throw std::runtime_error("unknown mode");
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
