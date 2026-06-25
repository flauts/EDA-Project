#ifndef RBTREECOUNT_H
#define RBTREECOUNT_H

#include <iostream>
#include <vector>
#include <cassert>
#include <stdexcept>
#include "bst.hpp"

using namespace std;

struct RBNodeInfo {
    bool red = true;
};

template <typename K, typename V>
using RBNode = BSTNode<K, V, RBNodeInfo>;

template <typename K, typename V>
class RedBlackTree : public BST<K, V, RBNodeInfo> {
   private:
    bool locked = false;

    void left_rotate(RBNode<K, V> *node) {
        auto child = static_cast<RBNode<K, V>*>(node->right);
        node->right = child->left;
        if (node->right != nullptr) node->right->parent = node;
        child->parent = node->parent;
        node->parent = child;
        child->left = node;
        if (child->parent == nullptr) this->root = child;
        else if (child->parent->left == node) child->parent->left = child;
        else child->parent->right = child;
    }

    void right_rotate(RBNode<K, V> *node) {
        auto child = static_cast<RBNode<K, V>*>(node->left);
        node->left = child->right;
        if (node->left != nullptr) node->left->parent = node;
        child->parent = node->parent;
        node->parent = child;
        child->right = node;
        if (child->parent == nullptr) this->root = child;
        else if (child->parent->left == node) child->parent->left = child;
        else child->parent->right = child;
    }

    void fixupInsert(RBNode<K, V> *node) {
        this->root->info.red = false;
        if (node == nullptr || node->parent == nullptr || node->parent->parent == nullptr) return;
        auto parent = static_cast<RBNode<K, V>*>(node->parent);
        while (parent != nullptr && parent->info.red) {
            auto grandparent = static_cast<RBNode<K, V>*>(parent->parent);
            if (parent == grandparent->left) {
                auto uncle = static_cast<RBNode<K, V>*>(grandparent->right);
                if (uncle != nullptr && uncle->info.red) {
                    parent->info.red = false;
                    uncle->info.red = false;
                    grandparent->info.red = true;
                    node = grandparent;
                    parent = static_cast<RBNode<K, V>*>(grandparent->parent);
                } else {
                    if (node == parent->right) {
                        left_rotate(parent);
                        node = parent;
                        parent = static_cast<RBNode<K, V>*>(node->parent);
                    }
                    right_rotate(grandparent);
                    parent->info.red = false;
                    grandparent->info.red = true;
                }
            } else {
                auto uncle = static_cast<RBNode<K, V>*>(grandparent->left);
                if (uncle != nullptr && uncle->info.red) {
                    parent->info.red = false;
                    uncle->info.red = false;
                    grandparent->info.red = true;
                    node = grandparent;
                    parent = static_cast<RBNode<K, V>*>(grandparent->parent);
                } else {
                    if (node == parent->left) {
                        right_rotate(parent);
                        node = parent;
                        parent = static_cast<RBNode<K, V>*>(node->parent);
                    }
                    left_rotate(grandparent);
                    parent->info.red = false;
                    grandparent->info.red = true;
                }
            }
        }
        this->root->info.red = false;
    }

    RBNode<K, V>* search(RBNode<K, V>* current, K key) {
        while (current != nullptr) {
            if (current->key == key) return current;
            if (current->key > key) {
                if (current->left == nullptr) return current;
                current = static_cast<RBNode<K, V>*>(current->left);
                operations++;
            } else {
                if (current->right == nullptr) return current;
                current = static_cast<RBNode<K, V>*>(current->right);
                operations++;
            }
        }
        return current;
    }

   public:
    long long operations = 0;

    RedBlackTree() : BST<K, V, RBNodeInfo>() {}

    void lock() {
        locked = true;
        operations = 0;
    }

    void insert(K key, V val) override {
        if (locked) throw std::runtime_error("Tree is locked");
        auto node = new RBNode<K, V>(key, val, RBNodeInfo());
        if (this->root == nullptr) {
            this->root = node;
            node->info.red = false;
            return;
        }
        auto current = static_cast<RBNode<K, V>*>(this->root);
        RBNode<K, V>* parent = nullptr;
        while (current != nullptr) {
            parent = current;
            if (key == current->key) {
                current->val = val;
                delete node;
                return;
            }
            if (key < current->key) current = static_cast<RBNode<K, V>*>(current->left);
            else current = static_cast<RBNode<K, V>*>(current->right);
        }
        node->parent = parent;
        if (key < parent->key) parent->left = node;
        else parent->right = node;
        fixupInsert(node);
    }

    void remove(K key) override {
        throw std::runtime_error("remove not implemented");
    }

    RBNode<K, V>* find(K key) override {
        if (!locked) throw std::runtime_error("Tree not locked");
        if (this->root == nullptr) throw std::runtime_error("Tree empty");
        auto found = search(static_cast<RBNode<K, V>*>(this->root), key);
        if (found->key != key) throw std::runtime_error("Key not found");
        return found;
    }
};

#endif
