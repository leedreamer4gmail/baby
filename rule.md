# 编码规则
严格按照 lawcode.md 的规则编码，包括项目自己生成的代码

# 测试规则
严格按照lawtest.md方法进行测试和debug，包括项目自己进行的测试，输出都用<本系统的文字>

# 思考
- 需要思考的地方调用llm，所需要的llm的资料在llmconfig.json里，调用llm时要打印llm的名字以及为什么选择这个llm
- 思考模块传递给写代码模块的promt要严格按照 lawpromt.md 的规则写

# 存储数据
如果你觉得需要数据库可以调用chroma数据库，所需要的资料在也在llmconfig.json里