#pragma once
#include<bits/stdc++.h>

namespace median_lab
{
using namespace std;
using i64=int64_t;
using u64=uint64_t;
using Clock=chrono::steady_clock;
inline i64 ns(Clock::time_point a,Clock::time_point b)
{
    return chrono::duration_cast<chrono::nanoseconds>(b-a).count();
}
enum class Status {OK,FAIL_BRACKET,FAIL_SIZE,RETRY_LIMIT};
inline const char* name(Status s)
{
    switch(s)
    {
        case Status::OK: return "OK";
        case Status::FAIL_BRACKET: return "FAIL_BRACKET";
        case Status::FAIL_SIZE: return "FAIL_SIZE";
        default: return "RETRY_LIMIT";
    }
}
struct Phases {i64 sampling=0,sample_sort=0,scan=0,candidate_sort=0;};
struct Result
{
    Status status=Status::OK;
    i64 answer=0;
    size_t sample_size=0,j_low=0,j_high=0,candidate_size=0;
    bool low_clamped=false,high_clamped=false,rank_in_bracket=false,size_exceeded=false;
    size_t attempts=0,bracket_failures=0,size_failures=0;
    Phases phases;
};
inline void validate_alpha(double alpha)
{
    if(!isfinite(alpha) || alpha<=0) throw invalid_argument("alpha must be finite and positive");
}
inline size_t sample_count(size_t n)
{
    if(n==0 || n>10000000) throw invalid_argument("n must be in 1..10000000");
    using Wide=unsigned __int128;
    Wide cube=Wide(n)*n*n;
    auto fourth=[](size_t x) {return Wide(x)*x*x*x;};
    size_t s=size_t(ceil(pow((long double)n,0.75L)));
    while(s>1 && fourth(s-1)>=cube) --s;
    while(fourth(s)<cube) ++s;
    return s;
}
inline i64 checked_reference(const vector<i64>& input)
{
    sample_count(input.size());
    auto sorted=input;
    sort(sorted.begin(),sorted.end());
    if(adjacent_find(sorted.begin(),sorted.end())!=sorted.end())
        throw invalid_argument("duplicate values are not supported");
    return sorted[sorted.size()/2];
}
struct RandomIndex
{
    mt19937_64& rng;
    size_t operator()(size_t n)
    {
        u64 bound=u64(n),threshold=(u64(0)-bound)%bound,value;
        do {value=rng();} while(value<threshold);
        return size_t(value%bound);
    }
};
template<class Sampler>
Result attempt(const vector<i64>& input,double alpha,Sampler& sampler,bool diagnostic=false)
{
    Result out;
    const size_t n=input.size(),r=n/2+1,s=sample_count(n);
    out.sample_size=s;
    out.attempts=1;
    vector<i64> sample(s);
    auto begin=Clock::time_point{};
    if(diagnostic) begin=Clock::now();
    for(auto& value:sample) value=input[sampler(n)];
    if(diagnostic) {auto end=Clock::now();out.phases.sampling=ns(begin,end);begin=end;}
    sort(sample.begin(),sample.end());
    if(diagnostic) {auto end=Clock::now();out.phases.sample_sort=ns(begin,end);}
    const long double half=(long double)s/2,width=(long double)alpha*sqrt((long double)n);
    long double lo=floor(half-width),hi=ceil(half+width);
    out.low_clamped=lo<1 || lo>s;
    out.high_clamped=hi<1 || hi>s;
    out.j_low=size_t(clamp(lo,1.0L,(long double)s));
    out.j_high=size_t(clamp(hi,1.0L,(long double)s));
    i64 d=sample[out.j_low-1],u=sample[out.j_high-1];
    size_t l_d=0,l_u=0;
    vector<i64> candidates;
    candidates.reserve(min(n,4*s+1));
    if(diagnostic) begin=Clock::now();
    for(i64 x:input)
    {
        if(x<d) ++l_d;
        else if(x>u) ++l_u;
        else candidates.push_back(x);
    }
    if(diagnostic) out.phases.scan=ns(begin,Clock::now());
    out.candidate_size=candidates.size();
    out.rank_in_bracket=l_d<r && r<=n-l_u;
    out.size_exceeded=candidates.size()>4*s;
    if(!out.rank_in_bracket) {out.status=Status::FAIL_BRACKET;out.bracket_failures=1;return out;}
    if(out.size_exceeded) {out.status=Status::FAIL_SIZE;out.size_failures=1;return out;}
    if(diagnostic) begin=Clock::now();
    sort(candidates.begin(),candidates.end());
    if(diagnostic) out.phases.candidate_sort=ns(begin,Clock::now());
    out.answer=candidates[r-l_d-1];
    return out;
}
template<class Sampler>
Result solve(const vector<i64>& input,double alpha,size_t limit,Sampler& sampler)
{
    if(limit==0) throw invalid_argument("max_attempts must be positive");
    size_t brackets=0,sizes=0;
    Result out;
    for(size_t k=1;k<=limit;++k)
    {
        out=attempt(input,alpha,sampler);
        brackets+=out.bracket_failures;
        sizes+=out.size_failures;
        out.attempts=k;
        out.bracket_failures=brackets;
        out.size_failures=sizes;
        if(out.status==Status::OK) return out;
    }
    out.status=Status::RETRY_LIMIT;
    return out;
}
inline vector<i64> permutation(size_t n,u64 seed)
{
    sample_count(n);
    vector<i64> values(n);
    for(size_t i=0;i<n;++i) values[i]=i64(i+1);
    mt19937_64 rng(seed);
    RandomIndex index{rng};
    for(size_t i=n;i>1;--i) swap(values[i-1],values[index(i)]);
    return values;
}
}
