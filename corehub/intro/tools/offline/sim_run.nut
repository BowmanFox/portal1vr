// usage: sq sim_run.nut   (expects sim_prelude.nut, sim_ents.nut, director.nut and sim_times.nut in the working dir)
dofile("sim_prelude.nut");
dofile("sim_ents.nut");        // fills simEnts from the map's named entities
dofile("director.nut");
dofile("sim_times.nut");       // simDumpTimes <- [..]; simStep <- 1/60
qaReferenceOpening = true; qaMouseLock = true;
function jnum(v) { return format("%.4f", v.tofloat()); }
function jvec(v) { return "[" + jnum(v.x) + "," + jnum(v.y) + "," + jnum(v.z) + "]"; }
function jstr(s) { local o = ""; foreach (ch in s) { if (ch == '"' || ch == '\\') o += "\\"; if (ch >= 32) o += ch.tochar(); } return "\"" + o + "\""; }
local dumpIdx = 0; local fireIdx = 0;
simTime = 0.0;
Start();
local n = 0;
while (dumpIdx < simDumpTimes.len()) {
    local t = n * simStep;
    simTime = t;
    if (n > 0) Tick();
    while (dumpIdx < simDumpTimes.len() && simDumpTimes[dumpIdx] <= t + 1e-6) {
        local line = "{\"t\":" + jnum(simDumpTimes[dumpIdx]) + ",\"simt\":" + jnum(t);
        line += ",\"eye\":" + jvec(PositionAt(t > 134 ? 134 : t)) + ",\"ang\":" + jvec(ReferenceAngles(t > 134 ? 134 : t)) + ",\"fov\":" + jnum(FilmFov(t));
        line += ",\"black\":" + screenBlackAlpha;
        line += ",\"ents\":{";
        local first = true;
        foreach (name, e in simEnts) {
            if (!e.touched) continue;
            if (!first) line += ","; first = false;
            line += jstr(name) + ":{\"o\":" + jvec(e.origin);
            foreach (k, v in e.kv) line += "," + jstr(k) + ":" + jstr(v);
            line += "}";
        }
        line += "},\"fires\":[";
        first = true;
        for (; fireIdx < simFires.len(); fireIdx++) {
            local f = simFires[fireIdx];
            if (!first) line += ","; first = false;
            line += "[" + jnum(f[0]) + "," + jstr(f[1]) + "," + jstr(f[2]) + "," + jstr(f[3]) + "]";
        }
        line += "]}";
        print(line + "\n");
        dumpIdx++;
    }
    n++;
}
