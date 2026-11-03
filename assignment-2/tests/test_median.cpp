#include "../src/median.hpp"
using namespace std;
using namespace median_lab;
size_t assertions=0,successful=0,allowed_failures=0;
void require(bool condition,const char* message)
{
    ++assertions;
    if(!condition) throw runtime_error(message);
}
template<class F> void rejects(F f)
{
    bool rejected=false;
    try {f();} catch(const invalid_argument&) {rejected=true;}
    require(rejected,"expected invalid_argument");
}
struct Sequence
{
    vector<size_t> indices;
    size_t position=0;
    size_t operator()(size_t n)
    {
        if(position>=indices.size() || indices[position]>=n) throw runtime_error("bad test sequence");
        return indices[position++];
    }
};
int main()
{
    try
    {
        const vector<double> alphas={0.125,0.25,0.5,1,1.5};
        for(size_t n:{1,2,3,4,5,16,63,64,65,100,1000})
        {
            auto random=permutation(n,1024);
            for(int layout=0;layout<3;++layout)
            {
                auto input=random;
                if(layout) sort(input.begin(),input.end());
                if(layout==2) reverse(input.begin(),input.end());
                for(auto& x:input) x=2*x-i64(n)-1;
                i64 ref=checked_reference(input);
                for(double alpha:alphas) for(u64 seed=0;seed<20;++seed)
                {
                    mt19937_64 rng(seed);
                    RandomIndex sampler{rng};
                    auto first=attempt(input,alpha,sampler);
                    if(first.status==Status::OK) {require(first.answer==ref,"wrong attempt answer");++successful;}
                    else {require(first.status==Status::FAIL_BRACKET || first.status==Status::FAIL_SIZE,"bad failure");++allowed_failures;}
                    auto result=solve(input,alpha,100,sampler);
                    require(result.status==Status::OK,"unexpected retry limit in coverage tests");
                    require(result.answer==ref,"wrong solved answer");
                }
            }
        }
        require(sample_count(1)==1 && sample_count(16)==8 && sample_count(10000)==1000,"sample rounding");
        require(checked_reference({-7,9})==9,"upper median convention");
        vector<i64> five={-9,-4,0,7,20};
        Sequence rank{{1,2,3,3}};
        auto correct=attempt(five,1,rank);
        require(correct.answer==0 && correct.candidate_size==3 && correct.rank_in_bracket,"rank conversion");
        Sequence twice{{0,0,0,0,0,1,2,4}};
        auto retried=solve(five,1,2,twice);
        require(retried.status==Status::OK && retried.attempts==2 && retried.bracket_failures==1,"retry uses fresh samples");
        Sequence all_low{{0,0,0,0,0,0,0,0}};
        auto exhausted=solve(five,1,2,all_low);
        require(exhausted.status==Status::RETRY_LIMIT && exhausted.attempts==2,"RETRY_LIMIT");
        auto big=permutation(10000,0);
        sort(big.begin(),big.end());
        Sequence wide;
        wide.indices.insert(wide.indices.end(),500,0);
        wide.indices.insert(wide.indices.end(),500,9999);
        auto oversized=attempt(big,0.5,wide);
        require(oversized.status==Status::FAIL_SIZE && oversized.rank_in_bracket && oversized.size_exceeded,"FAIL_SIZE");
        Sequence both;
        both.indices.insert(both.indices.end(),500,0);
        both.indices.insert(both.indices.end(),500,4999);
        auto simultaneous=attempt(big,0.5,both);
        require(simultaneous.status==Status::FAIL_BRACKET && !simultaneous.rank_in_bracket && simultaneous.size_exceeded,"simultaneous flags");
        Sequence one{{0}};
        auto tiny=attempt(vector<i64>{42},1.5,one);
        require(tiny.low_clamped && tiny.high_clamped && tiny.answer==42,"clamp reporting");
        rejects([] {checked_reference({});});
        rejects([] {checked_reference({1,1,2});});
        rejects([] {validate_alpha(0);});
        rejects([] {validate_alpha(-1);});
        rejects([] {validate_alpha(numeric_limits<double>::infinity());});
        rejects([] {validate_alpha(numeric_limits<double>::quiet_NaN());});
        rejects([&] {mt19937_64 rng(0);RandomIndex index{rng};solve(five,1,0,index);});
        cout << "PASS assertions=" << assertions << " successful_attempts=" << successful
                 << " allowed_failed_attempts=" << allowed_failures
                 << " branches=FAIL_BRACKET,FAIL_SIZE,RETRY_LIMIT,simultaneous_flags,clamping,duplicates,invalid\n";
    }
    catch(const exception& e) {cerr << "FAIL " << e.what() << '\n';return 1;}
}
