#include<bits/stdc++.h>
using namespace std;
#define ll long long
#define ull unsigned long long
using matrix=vector<vector<ll>>;
struct options
{
    string input,algorithm;
    int rounds=0;
    ull seed=0;
};
struct dataset
{
    int n=0;
    matrix a,b,c;
};
ull read_uint(const string& s)
{
    ull x=0;
    auto [pos,err]=from_chars(s.data(),s.data()+s.size(),x);
    if(s.empty() || err!=errc() || pos!=s.data()+s.size())
        throw runtime_error("invalid unsigned integer: "+s);
    return x;
}
options read_options(int argc,char* argv[])
{
    options opt;
    set<string> seen;
    for(int i=1;i<argc;i+=2)
    {
        string key=argv[i];
        if(i+1==argc) throw runtime_error("missing value for "+key);
        if(!seen.insert(key).second) throw runtime_error("duplicate option: "+key);
        string val=argv[i+1];
        if(key=="--input") opt.input=val;
        else if(key=="--algorithm") opt.algorithm=val;
        else if(key=="--rounds")
        {
            ull k=read_uint(val);
            if(!k || k>INT_MAX) throw runtime_error("rounds must be in 1..INT_MAX");
            opt.rounds=int(k);
        }
        else if(key=="--seed") opt.seed=read_uint(val);
        else throw runtime_error("unknown option: "+key);
    }
    for(string key:{"--input","--algorithm","--rounds","--seed"})
        if(!seen.count(key)) throw runtime_error("required option: "+key);
    if(opt.input.empty()) throw runtime_error("input path is empty");
    if(opt.algorithm!="exact" && opt.algorithm!="freivalds")
        throw runtime_error("algorithm must be exact or freivalds");
    return opt;
}
void read_matrix(ifstream& fin,matrix& a,int n,ll bound)
{
    a.assign(n,vector<ll>(n));
    string line,extra;
    for(int i=0;i<n;++i)
    {
        if(!getline(fin,line)) throw runtime_error("incomplete matrix");
        istringstream row(line);
        for(int j=0;j<n;++j)
        {
            if(!(row>>a[i][j])) throw runtime_error("invalid matrix element");
            if(a[i][j]<-bound || a[i][j]>bound)
                throw runtime_error("matrix element out of project range");
        }
        if(row>>extra) throw runtime_error("too many elements in matrix row");
    }
}
dataset read_input(const string& path)
{
    ifstream fin(path);
    if(!fin) throw runtime_error("cannot open input: "+path);
    dataset data;
    string line,extra;
    if(!getline(fin,line)) throw runtime_error("empty input");
    istringstream first(line);
    if(!(first>>data.n) || data.n<1 || data.n>1024 || (first>>extra))
        throw runtime_error("n must be in 1..1024 on a separate line");
    read_matrix(fin,data.a,data.n,9);
    read_matrix(fin,data.b,data.n,9);
    read_matrix(fin,data.c,data.n,81LL*data.n+2);
    if(getline(fin,line)) throw runtime_error("extra lines after matrices");
    return data;
}
bool check_exact(const dataset& data)
{
    for(int i=0;i<data.n;++i)
        for(int j=0;j<data.n;++j)
        {
            ll temp=0;
            for(int k=0;k<data.n;++k)
                temp+=data.a[i][k]*data.b[k][j];
            if(temp!=data.c[i][j]) return 0;
        }
    return 1;
}
bool check_freivalds(const dataset& data,int k,ull seed)
{
    mt19937_64 rng(seed);
    vector<ll> r(data.n),br(data.n);
    for(int round=0;round<k;++round)
    {
        for(int i=0;i<data.n;)
        {
            ull bits=rng();
            for(int bit=0;bit<64 && i<data.n;++bit,++i)
            {
                r[i]=bits&1ULL;
                bits>>=1;
            }
        }
        for(int i=0;i<data.n;++i)
        {
            ll sum=0;
            for(int j=0;j<data.n;++j)
                sum+=data.b[i][j]*r[j];
            br[i]=sum;
        }
        for(int i=0;i<data.n;++i)
        {
            ll abr=0,cr=0;
            for(int j=0;j<data.n;++j)
            {
                abr+=data.a[i][j]*br[j];
                cr+=data.c[i][j]*r[j];
            }
            if(abr!=cr) return false;
        }
    }
    // 随机向量生成与临时缓冲分配/初始化均属于核心计时范围。
    return true;
}
void solve(const options& opt)
{
    dataset data=read_input(opt.input);
    // 输入读取不计时；验证结果必须实际用于输出。
    auto start=chrono::steady_clock::now();
    bool accepted;
    if(opt.algorithm=="exact") accepted=check_exact(data);
    else accepted=check_freivalds(data,opt.rounds,opt.seed);
    auto finish=chrono::steady_clock::now();
    auto elapsed=chrono::duration_cast<chrono::nanoseconds>(finish-start).count();
    cout << "{\"accepted\":" << (accepted?"true":"false")
         << ",\"elapsed_ns\":" << elapsed
         << ",\"algorithm\":\"" << opt.algorithm << "\""
         << ",\"rounds\":" << opt.rounds
         << ",\"seed\":" << opt.seed << "}\n";
}
int main(int argc,char* argv[])
{
    ios::sync_with_stdio(0);cin.tie(0);cout.tie(0);
    try
    {
        options opt=read_options(argc,argv);
        solve(opt);
    }
    catch(const logic_error& e)
    {
        // 框架尚未实现时：非零退出、仅 stderr，不输出假答案或假耗时。
        cerr << "NOT IMPLEMENTED: " << e.what() << '\n';
        return 2;
    }
    catch(const exception& e)
    {
        cerr << "ERROR: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
