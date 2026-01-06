def get_root_exception(exc: BaseException) -> BaseException:
    """
    Docstring for get_root_exception
    
    :param exc: Description
    :type exc: BaseException
    :return: Description
    :rtype: BaseException

    """
    # usage 
    #   root = get_root_exception(e)
    #   message = f"{type(root).__name__}: {root}"
    
    while exc.__cause__ is not None:
        exc = exc.__cause__
    return exc

