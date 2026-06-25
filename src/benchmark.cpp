// M3 benchmark driver — processes M1 access traces through self-adjusting BSTs.

// g++ -std=c++17 -O2 -Isrc src/benchmark.cpp -o benchmark

#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <filesystem>
#include <algorithm>
#include <cmath>
#include <memory>
#include <iomanip>
#include <functional>
#include <set>

#include "trees/splaycount.hpp"
#include "trees/tangocount.hpp"
#include "trees/multisplaycount.hpp"
#include "trees/rbtreecount.hpp"

namespace fs = std::filesystem;

// ==============================================================
// Minimal JSON parser
// ==============================================================

struct JsonValue {
    enum Type { NUL, BOOL, NUMBER, STRING, ARRAY, OBJECT } type = NUL;
    std::string str;
    double num = 0;
    bool b = false;
    std::vector<JsonValue> arr;
    std::vector<std::pair<std::string, JsonValue>> obj;

    const JsonValue& operator[](const std::string& key) const {
        for (const auto& [k, v] : obj)
            if (k == key) return v;
        static const JsonValue nul;
        return nul;
    }
    const JsonValue& operator[](size_t i) const { return arr[i]; }
    size_t size() const { return arr.size(); }
    int as_int() const { return static_cast<int>(num); }
    const std::string& as_string() const { return str; }
};

class JsonParser {
    std::string s;
    size_t pos = 0;

    void skipws() {
        while (pos < s.size() && (s[pos]==' '||s[pos]=='\t'||s[pos]=='\n'||s[pos]=='\r'))
            ++pos;
    }

    char peek() { skipws(); return pos < s.size() ? s[pos] : '\0'; }
    char next() { skipws(); return pos < s.size() ? s[pos++] : '\0'; }

    JsonValue parse_value() {
        char c = peek();
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') return parse_string();
        if (c == 't' || c == 'f') return parse_bool();
        if (c == 'n') { pos += 4; return JsonValue{}; } // null
        return parse_number();
    }

    JsonValue parse_string() {
        next(); // consume opening "
        std::string val;
        while (pos < s.size() && s[pos] != '"') {
            if (s[pos] == '\\') { ++pos; if (pos < s.size()) val += s[pos++]; }
            else val += s[pos++];
        }
        if (pos < s.size()) ++pos; // consume closing "
        JsonValue jv;
        jv.type = JsonValue::STRING;
        jv.str = std::move(val);
        return jv;
    }

    JsonValue parse_number() {
        size_t start = pos;
        if (s[pos] == '-') ++pos;
        while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9') ++pos;
        if (pos < s.size() && s[pos] == '.') {
            ++pos;
            while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9') ++pos;
        }
        if (pos < s.size() && (s[pos]=='e'||s[pos]=='E')) {
            ++pos;
            if (pos < s.size() && (s[pos]=='+'||s[pos]=='-')) ++pos;
            while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9') ++pos;
        }
        JsonValue jv;
        jv.type = JsonValue::NUMBER;
        try {
            jv.num = std::stod(s.substr(start, pos - start));
        } catch (...) {
            jv.num = 0.0;
        }
        return jv;
    }

    JsonValue parse_bool() {
        if (s.substr(pos, 4) == "true") {
            pos += 4;
            JsonValue jv; jv.type = JsonValue::BOOL; jv.b = true; return jv;
        }
        pos += 5; // "false"
        JsonValue jv; jv.type = JsonValue::BOOL; jv.b = false;
        return jv;
    }

    JsonValue parse_object() {
        next(); // consume {
        JsonValue jv;
        jv.type = JsonValue::OBJECT;
        if (peek() == '}') { next(); return jv; }
        while (true) {
            auto key = parse_string();
            next(); // consume :
            jv.obj.emplace_back(std::move(key.str), parse_value());
            char c = next(); // consume , or }
            if (c == '}') return jv;
        }
    }

    JsonValue parse_array() {
        next(); // consume [
        JsonValue jv;
        jv.type = JsonValue::ARRAY;
        if (peek() == ']') { next(); return jv; }
        while (true) {
            jv.arr.push_back(parse_value());
            char c = next(); // consume , or ]
            if (c == ']') return jv;
        }
    }

public:
    explicit JsonParser(std::string str) : s(std::move(str)) {}
    JsonValue parse() { return parse_value(); }
};

// ==============================================================
// String helpers
// ==============================================================

static std::string fmtDouble2(double v) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2) << v;
    return ss.str();
}

// ==============================================================
// Phase metadata
// ==============================================================

struct Phase {
    std::string name;
    int start;
    int end;
};



// ==============================================================
// Wilber-1 Interleave Bound (IB-1)
// ==============================================================

#include <memory>

struct RefNode {
    int key;
    std::unique_ptr<RefNode> left;
    std::unique_ptr<RefNode> right;
    int preferred; // -1 = none, 0 = left, 1 = right
    RefNode(int k) : key(k), left(nullptr), right(nullptr), preferred(-1) {}
};

static std::unique_ptr<RefNode> buildRefTree(int lo, int hi) {
    if (lo > hi) return nullptr;
    int mid = (lo + hi) / 2;
    auto n = std::make_unique<RefNode>(mid);
    n->left = buildRefTree(lo, mid - 1);
    n->right = buildRefTree(mid + 1, hi);
    return n;
}

static int computeInterleaveBound(int n, const std::vector<int>& accesses) {
    auto root = buildRefTree(1, n);
    int count = 0;
    for (int x : accesses) {
        auto* v = root.get();
        while (v && v->key != x) {
            int np = (x < v->key) ? 0 : 1;
            if (v->preferred != np) {
                ++count;
                v->preferred = np;
            }
            v = (x < v->key) ? v->left.get() : v->right.get();
        }
    }
    return count;
}

// ==============================================================
// Trace metadata from manifest
// ==============================================================

struct TraceInfo {
    std::string trace_id;
    std::string family;
    int n;
    int m;
    std::string trace_path;
    std::string metadata_path;
};

// ==============================================================
// Template: run a single tree on a trace, return total operations
// ==============================================================

template <typename Tree>
long long runTree(const std::vector<int>& accesses, int n, int m,
                  const std::vector<Phase>& phases,
                  const std::string& csv_path, bool compact = false) {
    Tree tree;

    // Insert keys 1..n
    for (int k = 1; k <= n; ++k)
        tree.insert(k, k);

    tree.lock(); // freeze tree, reset operations to 0

    long long cum_ops = 0;
    if (compact) {
        for (int i = 0; i < m; ++i) {
            long long before = tree.operations;
            tree.find(accesses[i]);
            cum_ops += (tree.operations - before);
        }
        return cum_ops;
    }

    std::ofstream csv(csv_path);
    csv << "access_index,key,phase_id,phase_name,ops,cum_ops\n";

    size_t pid = 0;
    
    for (int i = 0; i < m; ++i) {
        while (pid < phases.size() && i >= phases[pid].end) {
            pid++;
        }
        
        int safe_pid = (pid < phases.size()) ? static_cast<int>(pid) : (phases.empty() ? -1 : static_cast<int>(phases.size() - 1));
        std::string ph_name = (safe_pid >= 0) ? phases[safe_pid].name : "unknown";

        int key = accesses[i];

        long long before = tree.operations;
        tree.find(key);
        long long cost = tree.operations - before;
        cum_ops += cost;

        csv << i << ',' << key << ',' << safe_pid << ',' << ph_name
            << ',' << cost << ',' << cum_ops << '\n';
    }
    return cum_ops;
}

// ==============================================================
// CLI argument parsing
// ==============================================================

struct Args {
    std::string traces_dir = "data/traces";
    std::string out_dir = "data/results";
    std::vector<std::string> trees;
    std::string single_trace; // empty = process all
    bool compact = false;
};

static Args parseArgs(int argc, char** argv) {
    Args a;
    a.trees = {"splay", "tango", "multisplay", "rbtree"};

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--traces" && i + 1 < argc)
            a.traces_dir = argv[++i];
        else if (arg == "--out" && i + 1 < argc)
            a.out_dir = argv[++i];
        else if (arg == "--trees" && i + 1 < argc) {
            a.trees.clear();
            std::string val = argv[++i];
            std::stringstream ss(val);
            std::string name;
            while (std::getline(ss, name, ','))
                a.trees.push_back(name);
        } else if (arg == "--trace" && i + 1 < argc)
            a.single_trace = argv[++i];
        else if (arg == "--compact")
            a.compact = true;
    }
    return a;
}

// ==============================================================
// Main
// ==============================================================

int main(int argc, char** argv) {
    auto args = parseArgs(argc, argv);

    // Read manifest or build single-trace list
    std::vector<TraceInfo> traces;

    if (!args.single_trace.empty()) {
        // Single trace mode: parse the trace's own JSON for metadata
        fs::path meta_path = fs::path(args.traces_dir) / args.single_trace / "trace.json";
        std::ifstream fin(meta_path);
        if (!fin.is_open()) {
            std::cerr << "Error: cannot open " << meta_path << std::endl;
            return 1;
        }
        std::string json_str((std::istreambuf_iterator<char>(fin)),
                              std::istreambuf_iterator<char>());
        auto jv = JsonParser(json_str).parse();

        TraceInfo ti;
        ti.trace_id = args.single_trace;
        ti.family = jv["family"].as_string();
        ti.n = jv["n"].as_int();
        ti.m = jv["m"].as_int();
        traces.push_back(ti);
    } else {
        fs::path manifest_path = fs::path(args.traces_dir) / "manifest.jsonl";
        std::ifstream fin(manifest_path);
        if (!fin.is_open()) {
            std::cerr << "Error: cannot open " << manifest_path << std::endl;
            return 1;
        }
        std::string line;
        while (std::getline(fin, line)) {
            if (line.empty()) continue;
            auto jv = JsonParser(line).parse();
            TraceInfo ti;
            ti.trace_id = jv["trace_id"].as_string();
            ti.family = jv["family"].as_string();
            ti.n = jv["n"].as_int();
            ti.m = jv["m"].as_int();
            ti.trace_path = jv["trace_path"].as_string();
            ti.metadata_path = jv["metadata_path"].as_string();
            traces.push_back(ti);
        }
    }

    // Create output directory
    fs::create_directories(args.out_dir);

    // Load completed runs to skip duplicates
    std::set<std::pair<std::string, std::string>> already_run;
    fs::path res_mf_path = fs::path(args.out_dir) / "results_manifest.jsonl";
    if (fs::exists(res_mf_path)) {
        std::ifstream exist_mf(res_mf_path);
        std::string line;
        while (std::getline(exist_mf, line)) {
            if (line.empty()) continue;
            auto rec = JsonParser(line).parse();
            already_run.insert({rec["trace_id"].as_string(), rec["tree"].as_string()});
        }
    }

    // Open results manifest in append mode
    std::ofstream results_manifest(res_mf_path, std::ios::app);

    int trace_count = 0;
    int csv_count = 0;

    // Tree dispatch table

    using TreeFn = std::function<long long(const std::vector<int>&, int, int,
                                            const std::vector<Phase>&,
                                            const std::string&, bool)>;
    std::vector<std::pair<std::string, TreeFn>> tree_dispatch;
    tree_dispatch.reserve(4);
    tree_dispatch.emplace_back("splay", [](const std::vector<int>& acc, int n, int m,
                                            const std::vector<Phase>& phases,
                                            const std::string& path, bool cmp) {
        return runTree<SplayTree<int,int>>(acc, n, m, phases, path, cmp);
    });
    tree_dispatch.emplace_back("tango", [](const std::vector<int>& acc, int n, int m,
                                            const std::vector<Phase>& phases,
                                            const std::string& path, bool cmp) {
        return runTree<TangoTree<int,int>>(acc, n, m, phases, path, cmp);
    });
    tree_dispatch.emplace_back("multisplay", [](const std::vector<int>& acc, int n, int m,
                                                  const std::vector<Phase>& phases,
                                                  const std::string& path, bool cmp) {
        return runTree<MultiSplayTree<int,int>>(acc, n, m, phases, path, cmp);
    });
    tree_dispatch.emplace_back("rbtree", [](const std::vector<int>& acc, int n, int m,
                                            const std::vector<Phase>& phases,
                                            const std::string& path, bool cmp) {
        return runTree<RedBlackTree<int,int>>(acc, n, m, phases, path, cmp);
    });

    size_t total_tasks = traces.size() * args.trees.size();
    size_t current_task = 0;

    for (const auto& ti : traces) {
        // Check if all requested trees are already run
        bool all_run = true;
        for (const auto& [tname, fn] : tree_dispatch) {
            if (std::find(args.trees.begin(), args.trees.end(), tname) != args.trees.end()) {
                if (!already_run.count({ti.trace_id, tname})) { all_run = false; break; }
            }
        }
        if (all_run) continue;

        // Read trace file
        fs::path trace_file = fs::path(args.traces_dir) / ti.trace_id / "trace.txt";
        std::ifstream tf(trace_file);
        if (!tf.is_open()) {
            std::cerr << "Warning: cannot open " << trace_file << " for trace "
                      << ti.trace_id << ", skipping" << std::endl;
            continue;
        }
        std::vector<int> accesses;
        accesses.reserve(ti.m);
        int key;
        while (tf >> key)
            accesses.push_back(key);
        if (static_cast<int>(accesses.size()) != ti.m) {
            std::cerr << "Warning: trace " << ti.trace_id << " has "
                      << accesses.size() << " accesses, expected " << ti.m
                      << ", skipping" << std::endl;
            continue;
        }

        // Read metadata JSON
        fs::path meta_path = fs::path(args.traces_dir) / ti.trace_id / "trace.json";
        std::ifstream mf(meta_path);
        if (!mf.is_open()) {
            std::cerr << "Warning: cannot open " << meta_path << " for trace "
                      << ti.trace_id << ", skipping" << std::endl;
            continue;
        }
        std::string json_str((std::istreambuf_iterator<char>(mf)),
                              std::istreambuf_iterator<char>());
        auto meta = JsonParser(json_str).parse();

        // Extract phases
        auto phases_val = meta["phases"];
        std::vector<Phase> phases;
        phases.reserve(phases_val.size());
        for (size_t i = 0; i < phases_val.size(); ++i) {
            Phase p;
            p.name  = phases_val[i]["name"].as_string();
            p.start = phases_val[i]["start"].as_int();
            p.end   = phases_val[i]["end"].as_int();
            phases.push_back(p);
        }

        // Compute Wilber-1 bound (same for all trees, computed once per trace)
        int ib1 = computeInterleaveBound(ti.n, accesses);

        // Create trace output directory
        fs::path trace_out_dir = fs::path(args.out_dir) / ti.trace_id;
        fs::create_directories(trace_out_dir);

        // Run each requested tree
        for (const auto& [tname, fn] : tree_dispatch) {
            if (std::find(args.trees.begin(), args.trees.end(), tname) == args.trees.end())
                continue;
            if (already_run.count({ti.trace_id, tname}))
                continue;

            ++current_task;
            int pct = (current_task * 100) / (total_tasks > 0 ? total_tasks : 1);
            std::cerr << "\r[" << std::setw(3) << pct << "%] Benchmarking: " 
                      << ti.trace_id << " (" << tname << ")        " << std::flush;

            std::string csv_path = (trace_out_dir / (tname + ".csv")).string();

            // Run tree: write per-access CSV, get total operations
            long long ops_total = fn(accesses, ti.n, ti.m, phases, csv_path, args.compact);

            double ratio = (ib1 > 0) ? (static_cast<double>(ops_total) / ib1) : 0.0;
            double avg   = (ti.m > 0) ? (static_cast<double>(ops_total) / ti.m) : 0.0;

            if (!args.compact) {
                // Append #AGG line to CSV (2 decimal places for doubles)
                std::ofstream csv_app(csv_path, std::ios::app);
                csv_app << "#AGG," << tname << ',' << ti.trace_id << ','
                        << ti.n << ',' << ti.m << ','
                        << ops_total << ',' << ib1 << ','
                        << fmtDouble2(ratio) << ',' << fmtDouble2(avg) << '\n';
            }

            // Write to results manifest (JSON numbers with 2 decimal places)
            results_manifest << "{\"trace_id\":\"" << ti.trace_id
                             << "\",\"family\":\"" << ti.family
                             << "\",\"n\":" << ti.n
                             << ",\"m\":" << ti.m
                             << ",\"tree\":\"" << tname
                             << "\",\"csv_path\":\"" << ti.trace_id << '/' << tname << ".csv"
                             << "\",\"ops_total\":" << ops_total
                             << ",\"interleave_bound\":" << ib1
                             << ",\"ratio_ops_ib1\":" << fmtDouble2(ratio)
                             << ",\"avg_ops_per_access\":" << fmtDouble2(avg)
                             << "}\n";

            ++csv_count;
        }
        ++trace_count;
    }
    std::cerr << "\n";

    std::cout << "Processed " << trace_count << " traces, wrote " << csv_count
              << " CSV files." << std::endl;

    return 0;
}
