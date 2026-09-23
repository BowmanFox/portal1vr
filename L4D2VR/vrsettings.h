#pragma once
#include <string>
#include <string_view>

namespace VrSettings {
enum class Command { None, Left, Right, Recenter };
inline Command Parse(std::string_view text) {
    const auto first=text.find_first_not_of(" \t\r\n");
    if(first==std::string_view::npos) return Command::None;
    text=text.substr(first,text.find_last_not_of(" \t\r\n")-first+1);
    if(text=="portal1vr_hand_left") return Command::Left;
    if(text=="portal1vr_hand_right") return Command::Right;
    if(text=="portal1vr_recenter") return Command::Recenter;
    return Command::None;
}
// Preserve unrelated settings, comments and existing line endings, including
// duplicate keys (the runtime parser otherwise lets the last duplicate win).
inline std::string SetBool(const std::string& input,const std::string& key,bool value) {
    std::string output;bool found=false;
    for(size_t pos=0;pos<input.size();) {
        const auto end=input.find('\n',pos);
        std::string line=input.substr(pos,end==std::string::npos ? input.size()-pos : end-pos+1);
        if(line.compare(0,key.size()+1,key+"=")==0) {
            auto suffix=line.find_first_of("#\r\n",key.size()+1);
            line=key+(value ? "=true" : "=false")+(suffix==std::string::npos ? "" : line.substr(suffix));
            found=true;
        }
        output+=line;
        if(end==std::string::npos) break;
        pos=end+1;
    }
    if(!found) {
        const char* newline=input.find("\r\n")!=std::string::npos ? "\r\n" : "\n";
        if(!output.empty() && output.back()!='\n') output+=newline;
        output+=key+(value ? "=true" : "=false")+newline;
    }
    return output;
}
}
