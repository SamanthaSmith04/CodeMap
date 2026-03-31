#include "buffer_mgmt.hpp"

BufferManager::BufferManager(int size) : maxSize(size) {}

void BufferManager::clearBuffer() {
    internalStore.clear();
}

bool BufferManager::pushData(const std::vector<char>& data) {
    if (internalStore.size() + data.size() > maxSize) return false;
    internalStore.insert(internalStore.end(), data.begin(), data.end());
    return true;
}