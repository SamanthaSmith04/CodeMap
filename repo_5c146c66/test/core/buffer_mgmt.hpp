#include <vector>

class BufferManager {
public:
    BufferManager(int size);
    void clearBuffer();
    bool pushData(const std::vector<char>& data);
private:
    int maxSize;
    std::vector<char> internalStore;
};