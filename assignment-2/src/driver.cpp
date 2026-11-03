#include "median.hpp"

using namespace std;
using namespace median_lab;
u64 uint_arg(const string& text)
{
    u64 value=0;
    auto [end,error]=from_chars(text.data(),text.data()+text.size(),value);
    if(text.empty() || error!=errc() || end!=text.data()+text.size())
        throw invalid_argument("invalid unsigned integer: "+text);
    return value;
}
int main(int argc,char** argv)
{
    try
    {
        map<string,string> args;
        for(int i=1;i<argc;i+=2)
        {
            if(i+1==argc || !args.emplace(argv[i],argv[i+1]).second)
                throw invalid_argument("missing value or duplicate option");
        }
        const vector<string> keys=
        {"--mode","--n","--dataset-seed","--trials","--warmups",
            "--max-attempts","--master-seed","--schedule-seed","--alphas","--output"};
        for(const auto& [key,value]:args)
            if(find(keys.begin(),keys.end(),key)==keys.end()) throw invalid_argument("unknown option: "+key);
        for(const auto& key:keys) if(!args.count(key)) throw invalid_argument("missing option: "+key);
        auto num=[&](const char* key) {return uint_arg(args.at(key));};
        size_t n=num("--n"),trials=num("--trials"),warmups=num("--warmups"),limit=num("--max-attempts");
        if(!trials || trials>1000000 || warmups>10000 || !limit || limit>1000000)
            throw invalid_argument("invalid trials, warmups or retry limit");
        sample_count(n);
        string mode=args.at("--mode");
        if(mode!="attempt" && mode!="solve" && mode!="diagnostic") throw invalid_argument("invalid mode");
        vector<double> alphas;
        istringstream list(args.at("--alphas"));
        string item;
        while(getline(list,item,','))
        {
            size_t end=0;
            double alpha=stod(item,&end);
            if(end!=item.size()) throw invalid_argument("invalid alpha");
            validate_alpha(alpha);
            if(find(alphas.begin(),alphas.end(),alpha)!=alphas.end()) throw invalid_argument("duplicate alpha");
            alphas.push_back(alpha);
        }
        if(alphas.empty()) throw invalid_argument("empty alphas");
        auto data=permutation(n,num("--dataset-seed"));
        i64 reference=checked_reference(data);
        ofstream out(args.at("--output"));
        if(!out) throw runtime_error("cannot open output file");
        out << "experiment,n,alpha,method,dataset_seed,sampling_seed,trial_id,status,sample_size,j_low,j_high,"
              "low_clamped,high_clamped,candidate_size,rank_in_bracket,size_exceeded,attempt_count,"
              "bracket_failures,size_failures,elapsed_ns,correctness,answer,reference,"
              "sampling_ns,sample_sort_ns,scan_ns,candidate_sort_ns\n";
        mt19937_64 seeds(num("--master-seed")),schedule(num("--schedule-seed"));
        size_t records=0;
        for(size_t rep=0;rep<warmups+trials;++rep)
        {
            u64 seed=seeds();
            vector<int> order;
            for(size_t a=0;a<alphas.size();++a) order.push_back(int(a));
            if(mode=="solve") order.push_back(-1);
            RandomIndex shuffle_index{schedule};
            for(size_t i=order.size();i>1;--i) swap(order[i-1],order[shuffle_index(i)]);
            for(int setting:order)
            {
                auto input=data;
                Result result;
                const bool baseline=setting<0;
                double alpha=baseline?0:alphas[size_t(setting)];
                auto start=Clock::now();
                if(baseline)
                {
                    sort(input.begin(),input.end());
                    result.answer=input[n/2];
                    result.attempts=1;
                }
                else
                {
                    mt19937_64 rng(seed);
                    RandomIndex index{rng};
                    if(mode=="solve") result=solve(input,alpha,limit,index);
                    else result=attempt(input,alpha,index,mode=="diagnostic");
                }
                i64 elapsed=ns(start,Clock::now());
                bool success=result.status==Status::OK;
                if(success && result.answer!=reference) throw runtime_error("WRONG ANSWER");
                if(rep<warmups) continue;
                ++records;
                out << mode << ',' << n << ',' << setprecision(12) << alpha << ',' << (baseline?"sort":"randomized")
                   << ',' << num("--dataset-seed") << ',' << seed << ',' << rep-warmups << ',' << name(result.status)
                   << ',' << result.sample_size << ',' << result.j_low << ',' << result.j_high
                   << ',' << result.low_clamped << ',' << result.high_clamped << ',' << result.candidate_size
                   << ',' << result.rank_in_bracket << ',' << result.size_exceeded << ',' << result.attempts
                   << ',' << result.bracket_failures << ',' << result.size_failures << ',' << elapsed << ','
                   << (success?"true":"NA") << ',';
                if(success) out << result.answer;
                out << ',' << reference << ',' << result.phases.sampling << ',' << result.phases.sample_sort
                   << ',' << result.phases.scan << ',' << result.phases.candidate_sort << '\n';
            }
        }
        out.flush();
        if(!out) throw runtime_error("output write failed");
        cout << "PASS " << mode << " n=" << n << " dataset_seed=" << num("--dataset-seed") << " records=" << records << '\n';
    }
    catch(const exception& e)
    {
        cerr << "ERROR: " << e.what() << '\n';
        return 1;
    }
}
