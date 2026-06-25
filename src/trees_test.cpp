#include <iostream>
#include <vector>
#include <cassert>

#include "trees/splaycount.hpp"
#include "trees/tangocount.hpp"
#include "trees/multisplaycount.hpp"
#include "trees/rbtreecount.hpp"

using namespace std;

constexpr int N = 31;

// Helper: in-order traversal collecting keys into a vector
template <typename Node>
void inorder_collect(Node* node, vector<int>& keys) {
    if (!node) return;
    inorder_collect(node->left, keys);
    keys.push_back(node->key);
    inorder_collect(node->right, keys);
}

// ----------------------------------------------------------------
// 1. test_search_consistency
//    Insert 1..31, lock(), find(k) for every k, assert key matches.
// ----------------------------------------------------------------
void test_search_consistency() {
    cout << "  [test_search_consistency]" << endl;

    // SplayTree
    {
        SplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k = 1; k <= N; ++k) {
            auto* node = tree.find(k);
            assert(node->key == k);
        }
    }

    // TangoTree
    {
        TangoTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k = 1; k <= N; ++k) {
            auto* node = tree.find(k);
            assert(node->key == k);
        }
    }

    // MultiSplayTree
    {
        MultiSplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k = 1; k <= N; ++k) {
            auto* node = tree.find(k);
            assert(node->key == k);
        }
    }

    // RedBlackTree
    {
        RedBlackTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k = 1; k <= N; ++k) {
            auto* node = tree.find(k);
            assert(node->key == k);
        }
    }

    cout << "    PASSED" << endl;
}

// ----------------------------------------------------------------
// 2. test_bst_order
//    Insert 1..31, lock(), perform a sequence of finds, then
//    in-order walk and verify keys are sorted 1..31.
// ----------------------------------------------------------------
void test_bst_order() {
    cout << "  [test_bst_order]" << endl;

    vector<int> expected;
    for (int i = 1; i <= N; ++i) expected.push_back(i);

    int seq[] = {5, 10, 15, 20, 25, 1, 31, 16};

    // SplayTree
    {
        SplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k : seq) tree.find(k);
        vector<int> keys;
        inorder_collect(tree.root, keys);
        assert(keys == expected);
    }

    // TangoTree
    {
        TangoTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k : seq) tree.find(k);
        vector<int> keys;
        inorder_collect(tree.root, keys);
        assert(keys == expected);
    }

    // MultiSplayTree
    {
        MultiSplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k : seq) tree.find(k);
        vector<int> keys;
        inorder_collect(tree.root, keys);
        assert(keys == expected);
    }

    cout << "    PASSED" << endl;
}

// ----------------------------------------------------------------
// 3. test_splay_root_property
//    SplayTree only: after find(k), assert tree.root->key == k.
// ----------------------------------------------------------------
void test_splay_root_property() {
    cout << "  [test_splay_root_property]" << endl;

    SplayTree<int, int> tree;
    for (int k = 1; k <= N; ++k) tree.insert(k, k);
    tree.lock();

    int seq[] = {1, 15, 31, 7, 20};
    for (int k : seq) {
        tree.find(k);
        assert(tree.root->key == k);
    }

    cout << "    PASSED" << endl;
}

// ----------------------------------------------------------------
// 4. test_operations_counter
//    Insert 1..31, lock(), assert operations == 0.
//    find(1), assert operations > 0. Record ops, find(1) again,
//    assert operations increased.
// ----------------------------------------------------------------
void test_operations_counter() {
    cout << "  [test_operations_counter]" << endl;

    // SplayTree
    {
        SplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        assert(tree.operations == 0);
        tree.find(1);
        assert(tree.operations > 0);
        long long ops1 = tree.operations;
        tree.find(31);
        assert(tree.operations > ops1);
    }

    // TangoTree
    {
        TangoTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        assert(tree.operations == 0);
        tree.find(1);
        assert(tree.operations > 0);
        long long ops1 = tree.operations;
        tree.find(31);
        assert(tree.operations > ops1);
    }

    // MultiSplayTree
    {
        MultiSplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        assert(tree.operations == 0);
        tree.find(1);
        assert(tree.operations > 0);
        long long ops1 = tree.operations;
        tree.find(31);
        assert(tree.operations > ops1);
    }

    cout << "    PASSED" << endl;
}

// ----------------------------------------------------------------
// 5. test_check_integrity
//    Insert 1..31, lock(), perform several finds, call
//    checkIntegrity(). Pass if no assert fires.
// ----------------------------------------------------------------
void test_check_integrity() {
    cout << "  [test_check_integrity]" << endl;

    // SplayTree
    {
        SplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        tree.find(10); tree.find(20); tree.find(5);
        tree.find(25); tree.find(15);
        tree.checkIntegrity();
    }

    // TangoTree
    {
        TangoTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        tree.find(10); tree.find(20); tree.find(5);
        tree.find(25); tree.find(15);
        tree.checkIntegrity();
    }

    // MultiSplayTree
    {
        MultiSplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        tree.find(10); tree.find(20); tree.find(5);
        tree.find(25); tree.find(15);
        tree.checkIntegrity();
    }

    cout << "    PASSED" << endl;
}

// ----------------------------------------------------------------
// 6. test_sequential_access
//    Insert 1..31, lock(), access 1,2,3,...,31 in order.
//    Assert all finds succeed. Call checkIntegrity().
// ----------------------------------------------------------------
void test_sequential_access() {
    cout << "  [test_sequential_access]" << endl;

    // SplayTree
    {
        SplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k = 1; k <= N; ++k) {
            auto* node = tree.find(k);
            assert(node->key == k);
        }
        tree.checkIntegrity();
    }

    // TangoTree
    {
        TangoTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k = 1; k <= N; ++k) {
            auto* node = tree.find(k);
            assert(node->key == k);
        }
        tree.checkIntegrity();
    }

    // MultiSplayTree
    {
        MultiSplayTree<int, int> tree;
        for (int k = 1; k <= N; ++k) tree.insert(k, k);
        tree.lock();
        for (int k = 1; k <= N; ++k) {
            auto* node = tree.find(k);
            assert(node->key == k);
        }
        tree.checkIntegrity();
    }

    cout << "    PASSED" << endl;
}

// ----------------------------------------------------------------
// main
// ----------------------------------------------------------------
int main() {
    cout << "Running all tests..." << endl << endl;

    test_search_consistency();
    test_bst_order();
    test_splay_root_property();
    test_operations_counter();
    test_check_integrity();
    test_sequential_access();

    cout << endl << "ALL TESTS PASSED" << endl;
    return 0;
}
