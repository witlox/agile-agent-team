# C++ Coding Standards

## Enforced by Tools

All C++ code MUST conform to these tool-enforced standards:

### 1. clang-format (Formatter)
- **THE STANDARD** for C++ formatting
- **Style**: LLVM, Google, or Chromium (choose one)
- **Indentation**: 2 or 4 spaces (configurable)
- **Column limit**: 80-100 characters
- Run: `clang-format -i **/*.cpp **/*.h`
- Config in `.clang-format`:
```yaml
BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
PointerAlignment: Left
```

### 2. clang-tidy (Linter)
- **THE LINTER** for modern C++
- Checks: modernize, readability, performance, bugprone
- Run: `clang-tidy *.cpp -- -std=c++17`
- Config in `.clang-tidy`:
```yaml
Checks: >
  clang-diagnostic-*,
  clang-analyzer-*,
  modernize-*,
  readability-*,
  performance-*,
  bugprone-*,
  cppcoreguidelines-*
```

### 3. C++ Core Guidelines
- **Official modern C++ guidelines**
- Reference: https://isocpp.github.io/CppCoreGuidelines/
- Enforced by: clang-tidy with `cppcoreguidelines-*` checks
- Key rules:
  - Use RAII for resource management
  - Prefer `unique_ptr` over raw pointers
  - Use `const` by default
  - Avoid C-style casts

### 4. CMake (Build System)
- Standard build system for C++
- **Minimum version**: 3.15+
- Run: `cmake -B build && cmake --build build`
- Config in `CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.15)
project(MyProject VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)  # For clang-tidy

# Enable warnings
if(MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Wextra -Werror -pedantic)
endif()
```

### 5. GoogleTest (Testing)
- Standard testing framework
- Test files: `*_test.cpp`
- **Coverage requirement**: ≥80%
- Run: `ctest --output-on-failure`

## Non-Negotiable Patterns

### Naming Conventions (C++ Core Guidelines)
```cpp
// Classes, Structs, Enums: PascalCase
class UserAccount {};
struct Point { int x, y; };
enum class Status { Active, Inactive };

// Functions: camelCase or snake_case (choose one consistently)
int calculateTotal() {}           // camelCase (Google style)
int calculate_total() {}           // snake_case (LLVM style)

// Variables: camelCase or snake_case (match function style)
int userCount = 42;                // camelCase
int user_count = 42;               // snake_case

// Constants: kPascalCase or UPPER_SNAKE_CASE
constexpr int kMaxRetries = 3;     // Google style
constexpr int MAX_RETRIES = 3;     // LLVM style

// Template parameters: PascalCase
template<typename Item, typename Predicate>
class Container {};

// Namespaces: lowercase
namespace user_service {}
namespace http {}
```

### Modern C++ (C++17/20) - REQUIRED
```cpp
// Use auto for type inference
auto result = calculateTotal();
auto users = std::vector<User>{};

// Use nullptr (not NULL or 0)
User* user = nullptr;

// Use range-based for loops
for (const auto& user : users) {
    std::cout << user.name << '\n';
}

// Use structured bindings (C++17)
auto [id, name, email] = getUserData();

// Use std::optional for nullable values
std::optional<User> findUser(int id) {
    if (auto it = users.find(id); it != users.end()) {
        return it->second;
    }
    return std::nullopt;
}

// Use std::variant for sum types
using Result = std::variant<User, Error>;

// Use constexpr for compile-time constants
constexpr int kBufferSize = 1024;
```

### RAII (Resource Acquisition Is Initialization)
```cpp
// GOOD: Use RAII for resource management
class File {
public:
    explicit File(const std::string& filename)
        : file_(std::fopen(filename.c_str(), "r")) {
        if (!file_) {
            throw std::runtime_error("Failed to open file");
        }
    }

    ~File() {
        if (file_) {
            std::fclose(file_);
        }
    }

    // Delete copy, allow move
    File(const File&) = delete;
    File& operator=(const File&) = delete;
    File(File&& other) noexcept : file_(other.file_) {
        other.file_ = nullptr;
    }

private:
    FILE* file_;
};

// BAD: Manual resource management
FILE* file = fopen("file.txt", "r");
// ... (might forget to close)
fclose(file);
```

### Smart Pointers (Prefer over raw pointers)
```cpp
// Use unique_ptr for exclusive ownership
auto user = std::make_unique<User>("user@example.com");

// Use shared_ptr for shared ownership
auto shared_user = std::make_shared<User>("user@example.com");

// Use weak_ptr to break cycles
std::weak_ptr<User> weak_user = shared_user;

// Pass raw pointers only for non-owning references
void processUser(const User* user) {  // Non-owning, can be null
    if (user) {
        // Process
    }
}

// Pass references for non-null, non-owning access
void processUser(const User& user) {  // Non-owning, never null
    // Process
}
```

### Error Handling (Exceptions or Error Codes)
```cpp
// Option 1: Exceptions (preferred for libraries)
class UserError : public std::runtime_error {
public:
    explicit UserError(const std::string& msg)
        : std::runtime_error(msg) {}
};

User getUser(int id) {
    if (id <= 0) {
        throw UserError("Invalid user ID");
    }
    // ...
}

// Usage
try {
    auto user = getUser(123);
    std::cout << user.getName() << '\n';
} catch (const UserError& e) {
    std::cerr << "Error: " << e.what() << '\n';
} catch (const std::exception& e) {
    std::cerr << "Unexpected error: " << e.what() << '\n';
}

// Option 2: std::expected (C++23) or Result type
template<typename T, typename E>
class Result {
public:
    static Result Ok(T value) {
        return Result(std::move(value), true);
    }

    static Result Err(E error) {
        return Result(std::move(error), false);
    }

    bool isOk() const { return is_ok_; }
    const T& value() const { return value_; }
    const E& error() const { return error_; }

private:
    union {
        T value_;
        E error_;
    };
    bool is_ok_;
};
```

### Testing Pattern (GoogleTest)
```cpp
#include <gtest/gtest.h>
#include "user.h"

class UserTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Setup before each test
    }

    void TearDown() override {
        // Cleanup after each test
    }
};

TEST_F(UserTest, CreateUserWithValidEmail) {
    User user("test@example.com", "John Doe");

    EXPECT_EQ(user.getEmail(), "test@example.com");
    EXPECT_EQ(user.getName(), "John Doe");
}

TEST_F(UserTest, ThrowsOnInvalidEmail) {
    EXPECT_THROW({
        User user("invalid-email", "John Doe");
    }, std::invalid_argument);
}

// Parameterized tests
class CalculateTest : public ::testing::TestWithParam<std::tuple<int, int, int>> {};

TEST_P(CalculateTest, AdditionWorks) {
    auto [a, b, expected] = GetParam();
    EXPECT_EQ(add(a, b), expected);
}

INSTANTIATE_TEST_SUITE_P(
    BasicAddition,
    CalculateTest,
    ::testing::Values(
        std::make_tuple(1, 2, 3),
        std::make_tuple(0, 0, 0),
        std::make_tuple(-1, 1, 0)
    )
);
```

### Documentation (Doxygen)
```cpp
/**
 * @brief Retrieves a user by their unique ID.
 *
 * @param id The unique user identifier (must be positive).
 * @return The user if found.
 * @throws UserNotFoundError If user doesn't exist.
 * @throws std::invalid_argument If id is non-positive.
 *
 * Example:
 * @code
 * try {
 *     auto user = getUser(123);
 *     std::cout << user.getName() << '\n';
 * } catch (const UserNotFoundError& e) {
 *     std::cerr << e.what() << '\n';
 * }
 * @endcode
 */
User getUser(int id);
```

### Const Correctness (ENFORCE)
```cpp
// Mark member functions const if they don't modify state
class User {
public:
    std::string getName() const { return name_; }  // const - doesn't modify
    void setName(const std::string& name) { name_ = name; }  // non-const

    // Pass by const reference for read-only parameters
    bool hasEmail(const std::string& email) const {
        return email_ == email;
    }

private:
    std::string name_;
    std::string email_;
};

// Use const for variables that don't change
const int kMaxRetries = 3;
const auto users = loadUsers();
```

### Move Semantics (C++11+)
```cpp
class Buffer {
public:
    // Constructor
    explicit Buffer(size_t size)
        : data_(new char[size]), size_(size) {}

    // Destructor
    ~Buffer() { delete[] data_; }

    // Copy constructor (deep copy)
    Buffer(const Buffer& other)
        : data_(new char[other.size_]), size_(other.size_) {
        std::copy(other.data_, other.data_ + size_, data_);
    }

    // Move constructor (transfer ownership)
    Buffer(Buffer&& other) noexcept
        : data_(other.data_), size_(other.size_) {
        other.data_ = nullptr;
        other.size_ = 0;
    }

    // Copy assignment
    Buffer& operator=(const Buffer& other) {
        if (this != &other) {
            delete[] data_;
            size_ = other.size_;
            data_ = new char[size_];
            std::copy(other.data_, other.data_ + size_, data_);
        }
        return *this;
    }

    // Move assignment
    Buffer& operator=(Buffer&& other) noexcept {
        if (this != &other) {
            delete[] data_;
            data_ = other.data_;
            size_ = other.size_;
            other.data_ = nullptr;
            other.size_ = 0;
        }
        return *this;
    }

private:
    char* data_;
    size_t size_;
};
```

## Toolchain Commands

```bash
# Format code (ALWAYS run before commit)
find . -name '*.cpp' -o -name '*.h' | xargs clang-format -i

# Lint code
clang-tidy *.cpp -- -std=c++17

# Build with CMake
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build

# Run tests
cd build && ctest --output-on-failure

# All checks (CI pipeline)
cmake -B build && cmake --build build && ctest --test-dir build
```

## C++ Best Practices (Core Guidelines)

1. **Use RAII** - Every resource should have an owning object
2. **Prefer stack to heap** - Use value semantics when possible
3. **Use smart pointers** - Avoid raw `new`/`delete`
4. **Make interfaces explicit** - Clear function contracts
5. **Use `const` everywhere possible** - Const correctness is mandatory
6. **Avoid C-style casts** - Use `static_cast`, `dynamic_cast`, etc.
7. **Use `auto` judiciously** - For type inference, not to hide types
8. **Zero-overhead principle** - Don't pay for what you don't use

## Deviations Allowed Only For

1. **Line length**: Can exceed 100 chars for:
   - Template declarations
   - Long string literals

2. **Raw pointers**: Can use only for:
   - Non-owning references
   - C API interop
   - Performance-critical code (documented)

3. **Test coverage**: Can be <80% for:
   - Platform-specific code
   - Unreachable error paths

**All deviations MUST be justified with comments.**

## Common Mistakes to Avoid

```cpp
// BAD: Using raw new/delete
User* user = new User();
delete user;

// GOOD: Use smart pointers
auto user = std::make_unique<User>();

// BAD: Not marking const
class User {
    std::string getName() { return name_; }
};

// GOOD: Mark read-only methods const
class User {
    std::string getName() const { return name_; }
};

// BAD: Catching exceptions by value (copies!)
try {
    // ...
} catch (std::exception e) {  // BAD: Copies exception
    // ...
}

// GOOD: Catch by const reference
try {
    // ...
} catch (const std::exception& e) {
    // ...
}

// BAD: Using C-style casts
double d = (double)integer;

// GOOD: Use C++ casts
double d = static_cast<double>(integer);

// BAD: Not using explicit for single-arg constructors
class User {
    User(std::string email) : email_(email) {}  // Allows implicit conversion
};

// GOOD: Use explicit
class User {
    explicit User(std::string email) : email_(email) {}
};
```
