#include <llvm/MC/MCContext.h>
#include <llvm/MC/MCDisassembler/MCDisassembler.h>
#include <llvm/MC/MCAsmInfo.h>
#include <llvm/MC/MCRegisterInfo.h>
#include <llvm/MC/MCInstrInfo.h>
#include <llvm/MC/MCSubtargetInfo.h>
#include <llvm/MC/MCTargetOptions.h>
#include <llvm/MC/TargetRegistry.h>
#include <llvm/Support/TargetSelect.h>
#include <llvm/Support/raw_ostream.h>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <vector>
#include <cstring>
using namespace llvm;
struct Row{unsigned lo,n;std::string group,sec;};
long long sx(unsigned n,unsigned bits){return ((long long)(n^(1u<<(bits-1))))-(1u<<(bits-1));}
int main(int argc,char**argv){
 InitializeAllTargetInfos();InitializeAllTargetMCs();InitializeAllDisassemblers();
 std::string err,tr="aarch64-unknown-linux-gnu";auto*t=TargetRegistry::lookupTarget(tr,err);if(!t)return 2;
 auto*r=t->createMCRegInfo(tr);auto*si=t->createMCSubtargetInfo(tr,"cortex-a57","+crypto,+crc");auto*mi=t->createMCInstrInfo();
 MCTargetOptions opt;auto*ai=t->createMCAsmInfo(*r,tr,opt);MCContext ctx(Triple(tr),ai,r,si);auto*ds=t->createMCDisassembler(*si,ctx);
 std::ifstream nr(argv[1],std::ios::binary),maskf("/audit/mask",std::ios::binary),sp("/audit/spans");
 std::vector<unsigned char> mask((std::istreambuf_iterator<char>(maskf)),{}),code(mask.size()*4);if(!nr.read((char*)code.data(),code.size()))return 2;
 std::ofstream stats("/audit/units.tsv"),issues("/audit/issues.tsv"),ops("/audit/opcodes.tsv");stats<<"group\tsections\twords\tdata_words\tdirect_branches\tindirect_branches\treturns\n";
 std::map<std::string,std::array<unsigned long,6>> totals;std::map<std::string,unsigned long> counts;
 Row row;while(sp>>row.lo>>row.n>>row.group>>row.sec){
 auto &v=totals[row.group];++v[0];
 for(unsigned pc=row.lo;pc<row.lo+row.n;pc+=4){
 if(!mask.at(pc/4)){v[2]++;continue;}v[1]++;
 MCInst inst;uint64_t sz=0;auto status=ds->getInstruction(inst,sz,ArrayRef<uint8_t>(&code[pc],4),pc,nulls());
 auto issue=[&](const char*why,std::string extra){issues<<row.group<<"\t"<<row.sec<<"\t"<<std::hex<<pc<<std::dec<<"\t"<<why<<"\t"<<extra<<"\n";};
 if(status!=MCDisassembler::Success || sz!=4){issue("decode",std::to_string(status));continue;}
 auto op=mi->getName(inst.getOpcode()).str();counts[op]++;
 unsigned w;memcpy(&w,&code[pc],4);long long target=-1;bool direct=true;
 if((w&0x7c000000)==0x14000000)target=pc+sx(w&0x03ffffff,26)*4;
 else if((w&0xff000010)==0x54000000||(w&0x7e000000)==0x34000000)target=pc+sx((w>>5)&0x7ffff,19)*4;
 else if((w&0x7e000000)==0x36000000)target=pc+sx((w>>5)&0x3fff,14)*4;
 else direct=false;
 if(direct){v[3]++;if(target<0||target/4>=(long long)mask.size()||!mask[target/4])issue("branch-target",std::to_string(target));}
 else if(op=="RET")v[5]++;else if(op=="BR"||op=="BLR")v[4]++;
 if(op=="BRK"||op=="HLT"||op=="HVC"||op=="SMC"||op=="UDF"||op=="ERET"||op=="SVC")issue("trap-or-supervisor",op);
 if(row.group!="glue" && (row.sec.find(".sub_")!=std::string::npos||row.sec.find(".d3d_orig_")!=std::string::npos)){
 const auto &desc=mi->get(inst.getOpcode());for(unsigned j=0;j<desc.getNumDefs()&&j<inst.getNumOperands();j++){const auto&o=inst.getOperand(j);if(o.isReg()){std::string dest=r->getName(o.getReg());if(dest=="X26"||dest=="X27"||dest=="X28"||dest=="W26"||dest=="W27"||dest=="W28")issue("reserved-def",op+":"+dest);}}
 }
 }}
 for(auto &kv:totals){stats<<kv.first;for(auto a:kv.second)stats<<"\t"<<a;stats<<"\n";}
 for(auto &kv:counts)ops<<kv.first<<"\t"<<kv.second<<"\n";
}
