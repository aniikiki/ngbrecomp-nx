using RecipeRankKey=std::array<unsigned,4>;
static std::map<RecipeRankKey,std::array<unsigned long long,3>> recipe_bins;
static void recipe_add(unsigned pc,unsigned prog,unsigned mask,unsigned group,unsigned long long ns){
 auto& v=recipe_bins[{pc,prog,mask,group}];++v[0];if(ns){++v[1];v[2]+=ns;}
}
extern "C" void recipe_rank_report(void){
 for(auto& [k,v]:recipe_bins)std::fprintf(stderr,"[RECIPE_RANK] %x %u %u %u %llu %llu %llu\n",k[0],k[1],k[2],k[3],v[0],v[1],v[2]);
}
