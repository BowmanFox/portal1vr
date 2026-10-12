// Offline stand-ins for the VScript engine API, so the real director.nut can be run outside the game.
class Vector {
    x = 0.0; y = 0.0; z = 0.0;
    constructor(_x = 0.0, _y = 0.0, _z = 0.0) { x = _x.tofloat(); y = _y.tofloat(); z = _z.tofloat(); }
    function _add(o) { return ::Vector(x + o.x, y + o.y, z + o.z); }
    function _sub(o) { return ::Vector(x - o.x, y - o.y, z - o.z); }
    function _mul(s) { if (typeof s == "instance") return ::Vector(x * s.x, y * s.y, z * s.z); return ::Vector(x * s, y * s, z * s); }
    function _div(s) { return ::Vector(x / s, y / s, z / s); }
    function _unm() { return ::Vector(-x, -y, -z); }
    function _tostring() { return "(vector : (" + x + ", " + y + ", " + z + "))"; }
    function Length() { return sqrt(x * x + y * y + z * z); }
    function LengthSqr() { return x * x + y * y + z * z; }
    function Length2D() { return sqrt(x * x + y * y); }
    function Dot(o) { return x * o.x + y * o.y + z * o.z; }
    function Cross(o) { return ::Vector(y * o.z - z * o.y, z * o.x - x * o.z, x * o.y - y * o.x); }
    function Norm() { local l = Length(); if (l > 0) { x /= l; y /= l; z /= l; } return l; }
    function ToKVString() { return x + " " + y + " " + z; }
}
simTime <- 0.0;
function Time() { return ::simTime; }
function printl(s) { ::simLog.append("" + s); }
simLog <- [];
simFires <- [];      // [time, target, action, value]
class SimEnt {
    name = ""; cls = ""; origin = null; kv = null; touched = false; scope = null;
    constructor(n, c, o) { name = n; cls = c; origin = o; kv = {}; }
    function SetOrigin(p) { origin = ::Vector(p.x, p.y, p.z); touched = true; }
    function GetOrigin() { return ::Vector(origin.x, origin.y, origin.z); }
    function SetVelocity(v) {}
    function GetVelocity() { return ::Vector(0, 0, 0); }
    function __KeyValueFromString(k, v) { kv[k] <- "" + v; touched = true; }
    function __KeyValueFromInt(k, v) { kv[k] <- "" + v; touched = true; }
    function __KeyValueFromFloat(k, v) { kv[k] <- "" + v; touched = true; }
    function ValidateScriptScope() { return true; }
    function GetScriptScope() { return ::getroottable(); }
    function GetForwardVector() { return ::Vector(1, 0, 0); }
    // no SetAngles / GetAngles: the 2009 engine has neither (a call stops the director with a script error);
    // turn props with __KeyValueFromString("angles", "p y r")
    function GetName() { return name; }
    function GetClassname() { return cls; }
    function IsValid() { return true; }
}
simEnts <- {};       // name -> SimEnt
simPlayer <- SimEnt("", "player", Vector(0, 0, 0));
Entities <- {
    function FindByName(prev, name) { if (prev != null) return null; if (name in ::simEnts) return ::simEnts[name]; return null; }
    function FindByClassname(prev, cls) { if (prev != null) return null; if (cls == "player") return ::simPlayer; foreach (n, e in ::simEnts) if (e.cls == cls) return e; return null; }
};
function EntFire(target, action, value = "", delay = 0.0, activator = null) {
    if (target == "intro_director" && action == "CallScriptFunction") return;   // the harness drives Tick itself
    ::simFires.append([::simTime + delay, target, action, "" + value]);
}
function EntFireByHandle(h, action, value = "", delay = 0.0, activator = null, caller = null) { ::simFires.append([::simTime + delay, h.name, action, "" + value]); }
