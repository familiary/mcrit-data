// Pulls a broad slice of libstdc++ and libgcc into a statically linked binary.
//
// This exists to fill a gap in data/MinGW: the x64 reports there contain
// libstdc++ and libsupc++ (thousands of std:: functions), while the x86
// reports contain none - only Win32 import thunks. So 32-bit libstdc++ is
// not covered anywhere in the corpus.
//
// Unlike every other recipe, this one links -static-libstdc++ -static-libgcc
// deliberately: here the runtime is the subject rather than contamination.

#include <algorithm>
#include <chrono>
#include <complex>
#include <deque>
#include <exception>
#include <forward_list>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <list>
#include <map>
#include <memory>
#include <numeric>
#include <random>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace {

struct Base {
    virtual ~Base() = default;
    virtual int value() const { return 1; }
};

struct Derived : Base {
    int value() const override { return 2; }
};

}  // namespace

extern "C" __declspec(dllexport) int exercise(const char *text, double number)
{
    int sink = 0;
    std::string subject(text);

    // Strings and streams.
    subject.append("-suffix").insert(0, "prefix-");
    sink += static_cast<int>(subject.find("suffix"));
    sink += static_cast<int>(subject.substr(2, 4).size());
    std::ostringstream out;
    out << std::setw(12) << std::setprecision(6) << std::fixed << number
        << std::hex << 255 << std::boolalpha << true << subject;
    std::istringstream in(out.str());
    std::string token;
    while (in >> token) sink += static_cast<int>(token.size());
    sink += static_cast<int>(std::stoi("123") + std::stod("1.5"));
    sink += static_cast<int>(std::to_string(number).size());

    // Containers.
    std::vector<int> vector{5, 3, 1, 4, 2};
    std::deque<int> deque(vector.begin(), vector.end());
    std::list<int> list(vector.begin(), vector.end());
    std::forward_list<int> flist(vector.begin(), vector.end());
    std::set<int> set(vector.begin(), vector.end());
    std::multiset<int> multiset(vector.begin(), vector.end());
    std::map<std::string, int> map{{"a", 1}, {"b", 2}};
    std::unordered_map<std::string, int> umap{{"a", 1}, {"b", 2}};
    std::unordered_set<int> uset(vector.begin(), vector.end());

    std::sort(vector.begin(), vector.end());
    std::stable_sort(deque.begin(), deque.end());
    list.sort();
    flist.sort();
    std::reverse(vector.begin(), vector.end());
    std::rotate(vector.begin(), vector.begin() + 1, vector.end());
    std::nth_element(vector.begin(), vector.begin() + 2, vector.end());
    sink += static_cast<int>(std::accumulate(vector.begin(), vector.end(), 0));
    sink += *std::max_element(vector.begin(), vector.end());
    sink += static_cast<int>(std::count_if(vector.begin(), vector.end(),
                                           [](int v) { return v > 2; }));
    sink += static_cast<int>(set.size() + multiset.size() + map.size() +
                             umap.size() + uset.size());

    // Smart pointers, polymorphism and RTTI.
    std::unique_ptr<Base> owned(new Derived());
    std::shared_ptr<Base> shared = std::make_shared<Derived>();
    std::weak_ptr<Base> weak = shared;
    sink += owned->value() + shared->value();
    sink += weak.expired() ? 0 : 1;
    if (auto *down = dynamic_cast<Derived *>(owned.get())) sink += down->value();

    // Exceptions and unwinding.
    try {
        throw std::runtime_error(subject);
    } catch (const std::runtime_error &error) {
        sink += static_cast<int>(std::string(error.what()).size());
    }
    try {
        (void)vector.at(999);
    } catch (const std::out_of_range &error) {
        sink += static_cast<int>(std::string(error.what()).size());
    }

    // std::function, regex, random, chrono, complex, numerics.
    std::function<int(int)> fn = [&sink](int v) { return v + sink; };
    sink += fn(1);
    std::regex pattern(R"((\w+)-(\w+))");
    std::smatch match;
    if (std::regex_search(subject, match, pattern)) sink += static_cast<int>(match.size());
    sink += static_cast<int>(std::regex_replace(subject, pattern, "$2").size());
    std::mt19937 engine(42);
    std::uniform_int_distribution<int> dist(0, 10);
    std::normal_distribution<double> normal(0.0, 1.0);
    sink += dist(engine) + static_cast<int>(normal(engine));
    auto now = std::chrono::steady_clock::now();
    sink += static_cast<int>(std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now() - now).count());
    std::complex<double> complex(number, 1.0);
    sink += static_cast<int>(std::abs(complex));

    // File streams.
    std::ofstream sinkfile;
    sinkfile.open("NUL");
    if (sinkfile) sinkfile << subject << std::endl;

    return sink;
}
