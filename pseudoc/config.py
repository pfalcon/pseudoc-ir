# Config options.

# Split basic block after a call instructions. Useful for tracking
# which variables are live after call (which then can be assigned
# to callee-save registers).
SPLIT_BB_AFTER_CALL = True
