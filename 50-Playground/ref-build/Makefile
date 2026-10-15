CXX      := clang++
CXXFLAGS := -std=c++17 -O2 -Wall -Wextra -Wpedantic
TARGET   := plugin_test
SRC      := plugin.cpp

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $< -o $@

test: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET)

# 交叉平台检查（本库工具，路径相对于仓库根）
check:
	bash ../tools/check_crossplatform.sh . || true
