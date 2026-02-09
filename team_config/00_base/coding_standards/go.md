# Go Coding Standards

## Enforced by Tools

All Go code MUST conform to these tool-enforced standards:

### 1. gofmt (Official Formatter)
- **THE STANDARD** - All Go code uses gofmt
- **Indentation**: Tabs (not spaces)
- **Brace style**: Opening brace on same line
- Run: `gofmt -w .` (auto-formats entire codebase)
- **NO CONFIGURATION** - gofmt defines Go style

### 2. goimports (Import Management)
- Extends gofmt with import organization
- Automatically adds/removes imports
- Groups: stdlib, external, internal
- Run: `goimports -w .`

### 3. golangci-lint (Linter Suite)
- Runs 50+ linters in parallel
- Includes: govet, staticcheck, errcheck, gosimple, ineffassign
- Run: `golangci-lint run`
- Config in `.golangci.yml`:
```yaml
linters:
  enable:
    - gofmt
    - govet
    - staticcheck
    - errcheck
    - gosimple
    - ineffassign
    - unused
    - misspell

run:
  timeout: 5m
  tests: true
```

### 4. go vet (Official Static Analyzer)
- Built into Go toolchain
- Catches suspicious constructs
- Run: `go vet ./...`
- Always passes before commit

### 5. go test (Testing)
- Test files: `*_test.go`
- Test functions: `func TestXxx(t *testing.T)`
- **Table-driven tests** are standard
- Run: `go test -v -race -cover ./...`
- **Coverage requirement**: ≥80%

## Non-Negotiable Patterns

### Naming Conventions (Enforced by golint)
```go
// Exported (public): PascalCase
type UserService struct {}
func GetUserByID(id int64) (*User, error) {}
const MaxRetries = 3

// Unexported (private): camelCase
func validateInput(s string) error {}
var userCache map[int64]*User

// Interfaces: Often end with -er
type Reader interface {
    Read(p []byte) (n int, err error)
}
```

### Error Handling (Required Pattern)
```go
// ALWAYS check errors immediately
result, err := riskyOperation()
if err != nil {
    return fmt.Errorf("operation failed: %w", err)
}

// NEVER ignore errors
_, _ = riskyOperation()  // BAD: golangci-lint will fail

// Use %w for error wrapping (Go 1.13+)
if err != nil {
    return fmt.Errorf("processing user %d: %w", id, err)
}
```

### Context Usage (Required for I/O)
```go
// All I/O operations MUST accept context
func GetUser(ctx context.Context, id int64) (*User, error) {
    // Check cancellation
    select {
    case <-ctx.Done():
        return nil, ctx.Err()
    default:
    }

    // Pass context downstream
    return db.QueryUserWithContext(ctx, id)
}
```

### Defer for Cleanup (Standard Pattern)
```go
func processFile(filename string) error {
    f, err := os.Open(filename)
    if err != nil {
        return err
    }
    defer f.Close()  // ALWAYS defer cleanup

    // Process file
    return process(f)
}
```

### Testing Pattern (Table-Driven)
```go
func TestCalculate(t *testing.T) {
    tests := []struct {
        name     string
        input    int
        expected int
    }{
        {"zero", 0, 0},
        {"positive", 5, 25},
        {"negative", -3, 9},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := calculate(tt.input)
            if result != tt.expected {
                t.Errorf("got %d, want %d", result, tt.expected)
            }
        })
    }
}
```

### Documentation (godoc Format)
```go
// Package user provides user management functionality.
//
// Example usage:
//
//     service := user.NewService(db)
//     user, err := service.GetUser(ctx, 123)
//
package user

// GetUser retrieves a user by ID.
//
// Returns ErrUserNotFound if the user does not exist.
func GetUser(ctx context.Context, id int64) (*User, error) {
    // Implementation
}
```

## Toolchain Commands

```bash
# Format code (ALWAYS run before commit)
gofmt -w .
goimports -w .

# Lint code
golangci-lint run

# Vet code
go vet ./...

# Run tests with race detector
go test -v -race -cover ./...

# All checks (CI pipeline)
gofmt -d . && go vet ./... && golangci-lint run && go test -race -cover ./...
```

## Go Proverbs (Design Principles)

These are NOT optional - they define idiomatic Go:

1. **"Errors are values"** - Handle errors explicitly, don't panic
2. **"Don't communicate by sharing memory; share memory by communicating"** - Use channels
3. **"Concurrency is not parallelism"** - Use goroutines and channels correctly
4. **"The bigger the interface, the weaker the abstraction"** - Keep interfaces small
5. **"Make the zero value useful"** - Structs should work with zero values
6. **"Accept interfaces, return structs"** - Function parameters should be interfaces

## Deviations Allowed Only For

1. **Line length**: No hard limit, but keep readable (~120 chars max)
2. **Comments**: Can skip for obvious private functions
3. **Test coverage**: Can be <80% for:
   - Platform-specific code
   - Unreachable error paths

**All deviations MUST be justified in code review comments.**

## Common Mistakes to Avoid

```go
// BAD: Ignoring errors
result, _ := operation()

// GOOD: Handle errors
result, err := operation()
if err != nil {
    return err
}

// BAD: Not using defer
f, _ := os.Open("file")
// ... (might forget to close)
f.Close()

// GOOD: Use defer
f, err := os.Open("file")
if err != nil {
    return err
}
defer f.Close()

// BAD: Goroutine leak
go func() {
    for {
        work()
    }
}()  // No way to stop!

// GOOD: Cancellable goroutine
ctx, cancel := context.WithCancel(context.Background())
go func() {
    for {
        select {
        case <-ctx.Done():
            return
        default:
            work()
        }
    }
}()
```
